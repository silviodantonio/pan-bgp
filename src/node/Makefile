proto_folder = ../proto
proto_filename = controller.proto 
proto_fullpath = $(proto_folder)/$(proto_filename) 
proto_out = . 

build: proto docker

proto: $(proto_fullpath) 
	python3 -m grpc_tools.protoc -I$(proto_folder) --python_out=$(proto_out) --grpc_python_out=$(proto_out) $(proto_fullpath)

docker: *.py requirements.txt
	pip freeze > requirements.txt
	docker build -t panbgp/node .
