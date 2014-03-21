"""The main driver for loading books.
"""
from ia import IADB
from ol import OpenLibrary
from config import config, load_config_from_args
import web

class Loader:
    def __init__(self):
        self.ia = IADB(config.ia_db)
        self.ol = OpenLibrary(config.ol_db)
        self.db = web.database(**config.db)

    def get_items(self, status=None, match_type=None, limit=1000):
        where = "1 = 1"
        if status:
            where += " AND status=$status"
        if match_type:
            where += " AND match_type=$match_type"
        result = self.db.query("SELECT * FROM bookloader WHERE " + where + " LIMIT $limit", vars=locals())
        d = dict((row.identifier, row) for row in result)
        ia_metadata = self.ia.get_metadata(d.keys())

        ol_keys = [row.match for row in d.values() if row.match]
        oldata = self.ol.get_metadata(ol_keys)

        def make_item(id):
            row = d[id]
            metadata = ia_metadata.get(id)
            ol = oldata.get(row.match)
            return Item(row, metadata=metadata, ol=ol)

        return [make_item(id) for id in ia_metadata]

    def get_summary(self):
        return {
            "status": self._group_by("status"),
            "match_type": self._group_by("match_type", where="status='matched'"),
        }
    def _group_by(self, column, where='1=1'):
        result = self.db.query("SELECT {0} as value, count(*) as count FROM bookloader WHERE {1} GROUP BY 1".format(column, where))
        return dict((row.value, row.count) for row in result)

    def load_identifiers(self, identifiers):
        for chunk in web.group(identifiers, 1000):
            chunk = list(set(chunk))
            result = self.db.query("SELECT identifier FROM bookloader WHERE identifier IN $chunk", vars=locals())
            present = set(row.identifier for row in result)
            data = [dict(identifier=id) for id in chunk if id not in present]
            if data:
                self.db.multiple_insert("bookloader", data)

    def load_identifiers_from_file(self, filename):
        self.load_identifiers(self._read_identifiers(filename))

    def _read_identifiers(self, filename):
        return (line.strip() for line in open(filename))

    def _get_pending_identifiers(self):
        result = self.db.query("SELECT * FROM bookloader WHERE status='pending'", vars=locals())
        return [row.identifier for row in result]

    def get_pending_identifiers_in_chunks(self, chunk_size=1000):
        id = 0
        while True:
            result = self.db.query("SELECT id, identifier FROM bookloader WHERE id > $id AND status='pending' LIMIT $chunk_size", vars=locals()).list()
            print "get_pending_identifiers_in_chunks id={0}, found {1} rows".format(id, len(result))
            if not result:
                break
            id = max(row.id for row in result)
            yield [row.identifier for row in result]
        print "** END get_pending_identifiers_in_chunks"

    def match(self):
        # mark invalid
        self.find_invalid()

        # match ocaid
        for identifiers in self.get_pending_identifiers_in_chunks():
            matches = self.ol.match_ocaid(identifiers)
            with self.db.transaction():
                for identifier,olkey in matches.items():
                    self.mark_matched(identifier, match_type="ocaid", match=olkey)
                if matches:
                    self.db.update("bookloader", where="identifier IN $ids", status="resolved", vars={"ids": matches.keys()})

        # match openlibrary
        self.match_openlibrary_field()

        # match isbn
        self.match_isbn()

    def mark_matched(self, identifier, match_type, match):
        #print "mark_matched", identifier, match_type, match
        self.db.update("bookloader", where="identifier=$identifier", 
            match_type=match_type, match=match, status="matched", 
            vars=locals())

    def match_openlibrary_field(self):
        for identifiers in self.get_pending_identifiers_in_chunks():
            metadata_dict = self.ia.get_metadata(identifiers)
            with self.db.transaction():
                for identifier, metadata in metadata_dict.items():
                    #print "identifier", metadata.get("openlibrary")
                    if metadata.get("openlibrary"):
                        self.mark_matched(identifier, match_type="openlibrary", match="/books/" + metadata['openlibrary'])

    def match_isbn(self):
        for identifiers in self.get_pending_identifiers_in_chunks(chunk_size=100):
            metadata_dict = self.ia.get_metadata(identifiers)

            def read_isbns():
                for identifier, metadata in metadata_dict.items():
                    if metadata.get('isbn'):
                        isbns = metadata['isbn'].split(';')
                        for isbn in isbns:
                            yield isbn, identifier

            isbn_to_ia = dict(read_isbns())
            isbn_to_ol = self.ol.match_isbns(isbn_to_ia.keys())

            ia_to_ol = dict((isbn_to_ia[isbn], isbn_to_ol[isbn]) for isbn in isbn_to_ol)

            with self.db.transaction():
                for identifier, book_key in ia_to_ol.items():
                    self.mark_matched(identifier, match_type="isbn", match=book_key)

    def find_invalid(self):
        for identifiers in self.get_pending_identifiers_in_chunks():
            metadata_dict = self.ia.get_metadata(identifiers)
            invalid = [id for id in identifiers if id not in metadata_dict]
            if invalid:
                self.db.update("bookloader", where="identifier IN $invalid", status="invalid", vars=locals())

class Item(web.storage):
    def __init__(self, *a, **kw):
        web.storage.__init__(self, *a, **kw)
        self.setdefault('metadata', {})

    @property
    def title(self):
        return self.metadata.get('title', '')

    @property
    def author(self):
        return self.metadata.get('creator', '')

    @property
    def isbns(self):
        return self.metadata.get('isbn', '') #.split(";")

    @property
    def openlibrary(self):
        return self.metadata.get("openlibrary", "")

if __name__ == "__main__":
    import sys
    load_config_from_args()
    if "--match" in sys.argv:
        Loader().match()
    else:
        Loader().load_identifiers_from_file(sys.argv[1])