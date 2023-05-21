import os
from proxypool.scheduler import Scheduler
import proxypool.processors.server as server
import argparse


parser = argparse.ArgumentParser(description='ProxyPool')
parser.add_argument('--processor', type=str, help='processor to run')
args = parser.parse_args()

if __name__ == '__main__':
    # if processor set, just run it
    if not os.path.exists(os.path.join(os.getcwd(), "users.db")):
        with server.app.app_context():
            server.db.create_all()
    if args.processor:
        getattr(Scheduler(), f'run_{args.processor}')()
    else:
        Scheduler().run()
