from leadforge.models import Business
from leadforge.models.enums import ContactKind, ContactSource
from leadforge.services import contacts as cx
from leadforge.services.dedup import domain_of, is_same_business, normalize_name

PAGE = """
<html><body>
<a href="mailto:Info@SampleClinic.example?subject=hi">Email us</a>
<p>Bookings: reception [at] sampleclinic [dot] example</p>
<img src="logo@2x.png">
<p>Call <a href="tel:+15125550142">(512) 555-0142</a></p>
<a href="https://wa.me/15125550142">WhatsApp</a>
<a href="https://www.instagram.com/sampleclinic/">Instagram</a>
<a href="/contact-us">Contact</a> <a href="/blog/post-1">Blog</a>
</body></html>
"""


def test_extract_emails_handles_mailto_and_obfuscation() -> None:
    found = {c.value: c for c in cx.extract_emails(PAGE, "https://sampleclinic.example/")}
    assert set(found) == {"info@sampleclinic.example", "reception@sampleclinic.example"}
    assert found["info@sampleclinic.example"].source == ContactSource.MAILTO
    assert all(c.source_url == "https://sampleclinic.example/" for c in found.values())


def test_extract_phones_and_links() -> None:
    phones = cx.extract_phones(PAGE, "https://sampleclinic.example/", "US")
    assert {p.value for p in phones} == {"+15125550142"}
    links = cx.extract_links(PAGE, "https://sampleclinic.example/")
    assert any(c.kind == ContactKind.WHATSAPP for c in links)
    assert any(c.kind == ContactKind.SOCIAL and "instagram" in c.value for c in links)


def test_candidate_pages_prefers_contact_pages() -> None:
    pages = cx.candidate_pages(PAGE, "https://sampleclinic.example/")
    assert pages[0] == "https://sampleclinic.example/contact-us"


async def test_validate_email_scores_site_domain_highest() -> None:
    async def mx(_domain: str) -> bool:
        return True

    own = cx.FoundContact(ContactKind.EMAIL, "info@sampleclinic.example", ContactSource.MAILTO, "u")
    free = cx.FoundContact(ContactKind.EMAIL, "sampleclinic@gmail.com", ContactSource.MAILTO, "u")
    await cx.validate_email(own, "sampleclinic.example", mx)
    await cx.validate_email(free, "sampleclinic.example", mx)
    assert own.confidence > free.confidence
    assert own.is_role_address is True
    assert cx.best_email([free, own]) is own


async def test_validate_email_without_mx_is_low_confidence() -> None:
    async def no_mx(_domain: str) -> bool:
        return False

    c = cx.FoundContact(ContactKind.EMAIL, "a@nomx.example", ContactSource.MAILTO, "u")
    await cx.validate_email(c, None, no_mx)
    assert c.confidence <= 0.1 and c.mx_valid is False


def _biz(name: str, phone: str | None = None, website: str | None = None) -> Business:
    return Business(
        name=name, normalized_name=normalize_name(name), phone_e164=phone,
        domain=domain_of(website), lat=12.97, lng=77.59,
    )  # fmt: skip


def test_dedup_matches_branch_listing_by_phone() -> None:
    a = _biz("Sample Smile Dental", "+918000000001", "https://smile.example")
    b = _biz("Sample Smile Dental (Branch Listing)", "+918000000001")
    c = _biz("Completely Different Bakery", "+918000000002")
    assert is_same_business(a, b)
    assert not is_same_business(a, c)


def test_domain_of_strips_www() -> None:
    assert domain_of("https://www.Sample.example/path") == "sample.example"
    assert domain_of(None) is None


def test_shared_phone_with_a_different_name_is_not_a_duplicate() -> None:
    a = _biz("Sample Smile Dental 01 Austin", "+15125550101")
    b = _biz("Sample Bistro 01 Austin", "+15125550101")
    assert not is_same_business(a, b)
    c = _biz("Dr. Smith Dental Clinic", "+15125550199")
    d = _biz("Smith Dental", "+15125550199")
    assert is_same_business(c, d)
