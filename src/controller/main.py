from concurrent import futures

import grpc

import controller_pb2       # Contains message type definitions
import controller_pb2_grpc  # Contains stubs and other stuf for building the server

# Implementation of the stub contained in pb2_grpc
class ControllerMessagingService(controller_pb2_grpc.ControllerMessagingServiceServicer):
    def SendNeighborsASN(self, request, context):
        print(f'Got AS list: {request.as_list}')
        return controller_pb2.ResponseStatus(status='OK')

def serve():
    port = "50051"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    controller_pb2_grpc.add_ControllerMessagingServiceServicer_to_server(ControllerMessagingService(), server)
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started, listening on " + port)
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
