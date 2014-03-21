import web

class IADB:
    def __init__(self, settings):
        self.db = web.database(**settings)

    def get_metadata(self, identifiers):
        """Returns metadata for a list of Identifiers.
        """
        if not identifiers:
            return {}
        result = self.db.query("""
            SELECT identifier, title, creator, 
                subject, publisher, date, 
                isbn, lccn, oclc_id, openlibrary, 
                collection, repub_state
            FROM metadata 
            WHERE identifier in $identifiers and repub_state != -1""", vars=locals())
        return dict((row.identifier, row) for row in result)
