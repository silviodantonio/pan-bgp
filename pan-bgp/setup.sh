#! /bin/bash

# Controller setup
cd controller/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

make

deactivate
cd ..

# Node setup
cd node/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

make

deactivate
cd ..
