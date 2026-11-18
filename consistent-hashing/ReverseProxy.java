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
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Level;
import java.util.logging.Logger;



class ConsistentHashing {

}


class MiniLoadBalancer {
    private final CopyOnWriteArrayList<String> servers;
    private final AtomicInteger currentIndex = new AtomicInteger(0);

    public MiniLoadBalancer(String[] urls) {
        if (urls.length <= 0) 
            throw new IllegalStateException("No URLs provided !");
        servers = new CopyOnWriteArrayList<>(urls);
    }

    public String getNextURL() {
        int size = servers.size();
        if (size <= 0) throw new IllegalStateException("No URLs available !");
        int idx = currentIndex.getAndUpdate(i -> (i + 1) % size) % size;
        return servers.get(idx);
    }
}


class ServerHandler implements HttpHandler {
    Logger logger = Logger.getLogger(ServerHandler.class.getName());

    private final String[] urls;

    // Hop-by-hop + headers HttpClient sets itself (Host, Content-Length, …)
    private final Set<String> HOP_BY_HOP_HEADERS = Set.of(
        "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
        "te", "trailers", "transfer-encoding", "upgrade", "content-length",
        "host", "expect"
    );

    private final HttpClient client = HttpClient
                                            .newBuilder()
                                            .connectTimeout(Duration.ofSeconds(10))
                                            .build();

    private final MiniLoadBalancer loadBalancer;

    public ServerHandler(String[] urls) {
        this.loadBalancer = new MiniLoadBalancer(urls);
        this.urls = urls;
    }

    private void translateHeaders(HttpHeaders clientResponseHeaders, Headers serverResponseHeaders) {
        for (Map.Entry<String, List<String>> entry: clientResponseHeaders.map().entrySet()) {
            String headerName = entry.getKey();
            if (HOP_BY_HOP_HEADERS.contains(headerName.toLowerCase()) || headerName.startsWith(":"))
                continue;
            serverResponseHeaders.put(headerName, entry.getValue());
        }
    }

    public static int hash(String key) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] encodedHash = digest.digest(key.getBytes(StandardCharsets.UTF_8));
            return ByteBuffer.wrap(encodedHash).getInt();
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    private String getConsistentURL(Headers rHeaders) {
        List<String> affinityHeaderList = rHeaders.get("x-user-id");
        if (affinityHeaderList == null || affinityHeaderList.isEmpty())
            return loadBalancer.getNextURL();
        String sessionAffinity = affinityHeaderList.getFirst();
        return this.urls[hash(sessionAffinity) % this.urls.length];
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

            logger.log(Level.INFO, () -> ">> [" + response.statusCode() + "]  |  " + urlString);

            translateHeaders(response.headers(), exchange.getResponseHeaders());
            byte[] body = response.body();
            exchange.sendResponseHeaders(response.statusCode(), body.length == 0 ? -1 : body.length);
            if (body.length > 0) {
                try (OutputStream os = exchange.getResponseBody()) {
                    os.write(body);
                }
            }
        } catch (InterruptedException ex) {

            logger.log(Level.SEVERE, () -> "Request interrupted: " + ex.getMessage());

            Thread.currentThread().interrupt();
            exchange.sendResponseHeaders(500, -1);
        } catch (Exception ex) {

            logger.log(Level.SEVERE, () -> "Request forwarding failed: " + ex.getMessage());

            exchange.sendResponseHeaders(502, -1);
        }

    }
}


class ReverseProxy {
    Logger logger = Logger.getLogger(ReverseProxy.class.getName());

    private final String[] URLS = {
        "http://127.0.0.1:9001",
        "http://127.0.0.1:9002",
        "http://127.0.0.1:9003"
    };
             
    public void listen(int port) {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
            server.createContext("/", new ServerHandler(URLS));
            server.setExecutor(null);
            server.start();
            logger.log(Level.INFO, () -> "Listening at " + port);

        } catch (IOException ex) {
            logger.log(Level.SEVERE, () -> "Failed to launch: " + ex.getMessage());
        }
    }

    void main(String[] args) {
        ReverseProxy server = new ReverseProxy();
        server.listen(9000);
    }
}