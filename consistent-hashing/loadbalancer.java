import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpHeaders;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;



class LoadBalancer {
    private static final String[] URLS = {
        "http://127.0.0.1:9001",
        "http://127.0.0.1:9002",
        "http://127.0.0.1:9003"
    };

    private static final HttpClient client = HttpClient
                                            .newBuilder()
                                            .connectTimeout(Duration.ofSeconds(10))
                                            .build();

    public static int hash(String key) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] encodedHash = digest.digest(key.getBytes(StandardCharsets.UTF_8));
            return ByteBuffer.wrap(encodedHash).getInt();
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    private static String scheduler() {
        Random random = new Random();
        int randomIdx = random.nextInt(URLS.length);
        return URLS[randomIdx];
    }
                                        
             
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

        // Hop-by-hop + headers HttpClient sets itself (Host, Content-Length, …)
        private static final Set<String> HOP_BY_HOP_HEADERS = Set.of(
            "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
            "te", "trailers", "transfer-encoding", "upgrade", "content-length",
            "host", "expect"
        );

        private void translateHeaders(HttpHeaders clientResponseHeaders, Headers serverResponseHeaders) {
            for (Map.Entry<String, List<String>> entry: clientResponseHeaders.map().entrySet()) {
                String headerName = entry.getKey();
                if (HOP_BY_HOP_HEADERS.contains(headerName.toLowerCase()) || headerName.startsWith(":"))
                    continue;
                serverResponseHeaders.put(headerName, entry.getValue());
            }
        }

        private String getConsistentURL(Headers rHeaders) {
            List<String> affinityHeaderList = rHeaders.get("x-user-id");
            if (affinityHeaderList == null || affinityHeaderList.isEmpty())
                return scheduler();
            String sessionAffinity = affinityHeaderList.getFirst();
            return URLS[hash(sessionAffinity) % URLS.length];
        }

        private HttpRequest buildRequest(String uri, String method, InputStream requestBodyStream, Headers rHeaders) {
            HttpRequest.Builder builder = HttpRequest
            .newBuilder()
            .uri(URI.create(uri))
            .method(
                method, 
                HttpRequest.BodyPublishers.ofInputStream(() -> requestBodyStream)
            );

            for (Map.Entry<String, List<String>> entry : rHeaders.entrySet()) {
                String key = entry.getKey();
                if (HOP_BY_HOP_HEADERS.contains(key.toLowerCase())) continue;
                for (String value : entry.getValue()) {
                    builder.setHeader(key, value);
                }
            }
            return builder.build();
        }

        @Override 
        public void handle(HttpExchange exchange) throws IOException {
            URI requestURI = exchange.getRequestURI();
            String rawPath = requestURI.getRawPath();
            String requestMethod = exchange.getRequestMethod();
            Headers requestHeaders = exchange.getRequestHeaders();
            InputStream requestBody = exchange.getRequestBody();

            String urlString = getConsistentURL(requestHeaders) + rawPath;

            try {
                HttpRequest request = buildRequest(urlString, requestMethod, requestBody, requestHeaders);
                HttpResponse<byte[]> response = client.send(request, HttpResponse.BodyHandlers.ofByteArray());
                System.out.println(">> [" + response.statusCode() + "]  |  " + urlString);
                translateHeaders(response.headers(), exchange.getResponseHeaders());
                byte[] body = response.body();
                exchange.sendResponseHeaders(response.statusCode(), body.length == 0 ? -1 : body.length);
                if (body.length > 0) {
                    try (OutputStream os = exchange.getResponseBody()) {
                        os.write(body);
                    }
                }
            } catch (InterruptedException ex) {
                System.err.println("Request forwarding failed: " + ex.getMessage());
                Thread.currentThread().interrupt();
                exchange.sendResponseHeaders(500, -1);
            } catch (Exception ex) {
                System.err.println("Request forwarding failed: " + ex.getMessage());
                exchange.sendResponseHeaders(502, -1);
            }

        }
    }

    void main(String[] args) {
        LoadBalancer server = new LoadBalancer();
        server.listen(9000);
    }
}