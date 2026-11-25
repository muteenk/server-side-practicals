import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.io.OutputStream;
import java.math.BigInteger;
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
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Level;
import java.util.logging.Logger;



class Hashing {
    public long hashToLongSHA256(String key) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] encodedHash = digest.digest(key.getBytes(StandardCharsets.UTF_8));
            
            int signed = ByteBuffer.wrap(encodedHash).getInt();
            return Integer.toUnsignedLong(signed);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    public BigInteger hashSHA256(String key) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] encodedHash = digest.digest(key.getBytes(StandardCharsets.UTF_8));
            return new BigInteger(1, encodedHash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }
}


abstract class ServerHashing {
    abstract String getServer(String sessionAffinity);
}


class ConsistentHashing extends ServerHashing{

    private final TreeMap<BigInteger, String> hashRing = new TreeMap<>();
    private final Hashing hashing = new Hashing();
    private final int VIRTUAL_NODES = 100;

    public ConsistentHashing(String[] urls) {
        if (urls.length < 1)
            throw new IllegalStateException("Atleast one urls must be provided");
        for (String url : urls) {
            for (int i = 0; i < VIRTUAL_NODES; i++) {
                BigInteger hashIdx = hashing.hashSHA256(url + "#" + i);
                hashRing.put(hashIdx, url);
            }
            
        }
    }

    public void addServer(String url) {
        for (int i = 0; i < VIRTUAL_NODES; i++) {
            BigInteger hashIdx = hashing.hashSHA256(url + "#" + i);
            hashRing.put(hashIdx, url);
        }
    }

    public String getServer(String sessionAffinity) {
        BigInteger hashIdx = hashing.hashSHA256(sessionAffinity);
        Map.Entry<BigInteger, String> entry = hashRing.ceilingEntry(hashIdx);
        if (entry == null) return hashRing.firstEntry().getValue();
        return entry.getValue();
    }
}


class ModuloHashing extends ServerHashing {

    private final CopyOnWriteArrayList<String> servers;
    private final Hashing hashing = new Hashing();

    public ModuloHashing(String[] urls) {
        if (urls.length <= 0) 
            throw new IllegalStateException("No URLs provided !");

        servers = new CopyOnWriteArrayList<>(urls);
    }

    public void addServer(String serverURL) {
        servers.add(serverURL);
    }

    public void removeServer() {
        servers.removeLast();
    }

    public String getServer(String sessionAffinity) {
        int index = (int) (hashing.hashToLongSHA256(sessionAffinity) % servers.size());
        return servers.get(index);
    }

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
                                            .followRedirects(HttpClient.Redirect.NEVER)
                                            .build();

    private final MiniLoadBalancer loadBalancer;
    private final ServerHashing serverHashing;

    public ServerHandler(String[] urls) {
        this.loadBalancer = new MiniLoadBalancer(urls);
        this.serverHashing = new ConsistentHashing(urls);
        this.urls = urls;
    }

    private void translateHeaders(HttpHeaders upstreamHeaders, Headers outboundHeaders) {
        for (Map.Entry<String, List<String>> entry: upstreamHeaders.map().entrySet()) {
            String headerName = entry.getKey();
            if (HOP_BY_HOP_HEADERS.contains(headerName.toLowerCase()) || headerName.startsWith(":"))
                continue;
            outboundHeaders.put(headerName, entry.getValue());
        }
    }

    private String getConsistentURL(Headers rHeaders) {
        List<String> affinityHeaderList = rHeaders.get("x-user-id");
        if (affinityHeaderList == null || affinityHeaderList.isEmpty())
            return loadBalancer.getNextURL();
        String sessionAffinity = affinityHeaderList.getFirst();
        return serverHashing.getServer(sessionAffinity);
    }

    private HttpRequest buildRequest(String uri, String method, byte[] requestBody, Headers rHeaders) {
        HttpRequest.BodyPublisher bodyPublisher = requestBody.length == 0
            ? HttpRequest.BodyPublishers.noBody()
            : HttpRequest.BodyPublishers.ofByteArray(requestBody);

        HttpRequest.Builder builder = HttpRequest
            .newBuilder()
            .uri(URI.create(uri))
            .timeout(Duration.ofSeconds(10))
            .method(method, bodyPublisher);

        for (Map.Entry<String, List<String>> entry : rHeaders.entrySet()) {
            String key = entry.getKey();
            if (HOP_BY_HOP_HEADERS.contains(key.toLowerCase())) continue;
            for (String value : entry.getValue()) {
                builder.setHeader(key, value);
            }
        }
        return builder.build();
    }

    private void sendError(HttpExchange exchange, int status) {
        try {
            exchange.sendResponseHeaders(status, -1);
        } catch (IOException ignored) {
            // Client may already be gone.
        }
    }

    @Override 
    public void handle(HttpExchange exchange) throws IOException {
        String rawPath = exchange.getRequestURI().getRawPath();
        String requestMethod = exchange.getRequestMethod();
        Headers requestHeaders = exchange.getRequestHeaders();
        boolean headersSent = false;

        try {
            byte[] requestBody = exchange.getRequestBody().readAllBytes();
            String urlString = getConsistentURL(requestHeaders) + rawPath;

            HttpRequest request = buildRequest(urlString, requestMethod, requestBody, requestHeaders);
            HttpResponse<byte[]> response = client.send(request, HttpResponse.BodyHandlers.ofByteArray());

            logger.log(Level.INFO, () -> ">> [" + response.statusCode() + "]  |  " + urlString);

            translateHeaders(response.headers(), exchange.getResponseHeaders());
            byte[] body = response.body() != null ? response.body() : new byte[0];
            long responseLength = body.length == 0 ? -1 : body.length;

            exchange.sendResponseHeaders(response.statusCode(), responseLength);
            headersSent = true;

            if (body.length > 0) {
                try (OutputStream os = exchange.getResponseBody()) {
                    os.write(body);
                }
            }
        } catch (InterruptedException ex) {
            logger.log(Level.SEVERE, () -> "Request interrupted: " + ex.getMessage());
            Thread.currentThread().interrupt();
            if (!headersSent) sendError(exchange, 500);
        } catch (Exception ex) {
            logger.log(Level.SEVERE, () -> "Request forwarding failed: " + ex);
            if (!headersSent) sendError(exchange, 502);
        } finally {
            exchange.close();
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
            HttpServer server = HttpServer.create(new InetSocketAddress(port), 1024);
            server.createContext("/", new ServerHandler(URLS));
            server.setExecutor(Executors.newCachedThreadPool());
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