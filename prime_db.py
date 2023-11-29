import yaml
from cxo_chat.services.auth import Auth
from cxo_chat.services.cosmosDB import CosmosDB
from cxo_chat.db.models import Base

# read yaml config file
with open('config.yaml') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

# authentication
auth = Auth(config)
auth.fake_login()

# create the util objects
cosmos_db = CosmosDB(config, auth)

if __name__ == '__main__':

    # create the tables
    Base.metadata.create_all(cosmos_db.engine)
