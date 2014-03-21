import os, sys
import yaml
import web

config = web.storage()

def process_db_config(config):
    if 'pw_file' in config:
        filename = config.pop('pw_file')
        config['pw'] = open(filename).read().strip()
    elif 'pw_script' in config:
        filename = config.pop('pw_script')
        config['pw'] = os.popen(filename).read().strip()    

def load_config(filename):
    global config

    d = yaml.load(open(filename))
    config.clear()
    config.update(d)
    process_db_config(config['ol_db'])
    process_db_config(config['ia_db'])
    process_db_config(config['db'])

    print "config", config.keys()
    return config


def load_config_from_args():
    global config

    if "--config" in sys.argv:
        index = sys.argv.index("--config")
        configfile = sys.argv[index+1]
        sys.argv = sys.argv[:index] + sys.argv[index+2:]
        return load_config(configfile)