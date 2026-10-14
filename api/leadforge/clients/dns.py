import dns.asyncresolver
import dns.exception
import dns.resolver


async def has_mx(domain: str) -> bool:
    resolver = dns.asyncresolver.Resolver()
    resolver.lifetime = 5.0
    try:
        answer = await resolver.resolve(domain, "MX")
        return len(answer) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        # RFC 5321: fall back to an A record when there is no MX.
        try:
            await resolver.resolve(domain, "A")
            return True
        except dns.exception.DNSException:
            return False
    except dns.exception.DNSException:
        return False


async def mock_has_mx(domain: str) -> bool:
    """Fixture domains (`.example`) and common providers accept mail; nothing else does."""
    return domain.endswith(".example") or domain in {"gmail.com", "outlook.com", "yahoo.com"}
