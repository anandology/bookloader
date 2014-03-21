"""Web application for looking it to the book loading process.
"""
import sys, os
import web
import config
from loader import Loader

urls = (
    "/", "index"
)
app = web.application(urls, globals())

tglobals = {
    'changequery': web.changequery,
    "isinstance": isinstance,
    "list": list,
    "sum": sum
}

path = os.path.join(os.path.dirname(__file__), "templates")
render = web.template.render(path, base="site", globals=tglobals)

class index:
    def GET(self):
        i = web.input(status=None, match_type=None)
        status = i.status or None
        match_type = i.match_type or None
        loader = Loader()
        items = loader.get_items(status=status, match_type=match_type)
        summary = loader.get_summary()
        return render.index(items, summary)

def main():
    if "--config" in sys.argv:
        index = sys.argv.index("--config")
        configfile = sys.argv[index+1]
        sys.argv = sys.argv[:index] + sys.argv[index+2:]        
        config.load_config(configfile)
    app.run()

if __name__ == "__main__":
    main()