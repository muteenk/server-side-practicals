import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;



class Server {
    public void listen(int port) {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
            server.createContext("/", new ServerHandler());
            server.setExecutor(null);
            server.start();
            System.out.println("Listening at " + port);

        } catch (IOException ex) {
            throw new RuntimeException("Failed to launch: " + ex.getMessage());
        }
    }

    static class ServerHandler implements HttpHandler {
        @Override 
        public void handle(HttpExchange exchange) throws IOException {
            URI requestURI = exchange.getRequestURI();
            String rawPath = requestURI.getRawPath();
            System.out.println(rawPath);
        }
    }
}


class LoadBalancer {
    void main(String[] args) {
        Server server = new Server();
        server.listen(9000);
    }
}