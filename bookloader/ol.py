import web
import json

class OpenLibrary:
    def __init__(self, settings):
        self.db = web.database(**settings)
        self.pids = {}

    def get_property_id(self, type, name):
        if (type, name) not in self.pids:
            self.pids[type, name] = self._get_property_id(type, name)
        return self.pids[type, name]

    def _get_property_id(self, type, name):
        result = self.db.query(
            "select id from property" +
            " where type=(select id from thing where key=$type)" +
            "   and name=$name", vars=locals())
        return result[0].id

    def match_ocaid(self, identifiers):
        """Tries to find if there are books with any of the given identifiers as ocaid.

        Returns a dictionary from identifier -> ol_key for all the matched identifiers.
        """
        return self.query_things("ocaid", identifiers)

    def match_isbns(self, isbns):
        """Returns books matching given ISBNs.
        """
        return self.query_things("isbn_", isbns)

    def query_things(self, property, values):
        """Queries ol db for all books where given property has one of the values.
        Returns a dict with mapping from value to book-key for all matches.
        """
        if not values:
            return {}
        key_id = self.get_property_id("/type/edition", property)
        result = self.db.query("SELECT thing.key as book_key, e.value as value FROM edition_str e, thing" +
            " WHERE thing.id=e.thing_id" + 
            "   AND e.key_id=$key_id"
            "   AND e.value IN $values", vars=locals())
        return dict((row.value, row.book_key) for row in result)

    def get_metadata(self, book_keys):
        if not book_keys:
            return {}
        result = self.db.query(
            "SELECT thing.key, data.data" +
            " FROM thing, data" +
            " WHERE data.thing_id=thing.id" +
            "   AND data.revision=thing.latest_revision" +
            "   AND thing.key in $book_keys",
            vars=locals())
        return dict((row.key, json.loads(row.data)) for row in result)
