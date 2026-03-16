import re

from lxml import etree


_CHAVE_RE = re.compile(r"\bNFe(\d{44})\b")


def parse_xml(xml_content: str):
    if isinstance(xml_content, bytes):
        xml_bytes = xml_content
    else:
        xml_bytes = (xml_content or "").encode("utf-8", errors="ignore")

    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=True, huge_tree=True)
    return etree.fromstring(xml_bytes, parser=parser)


def find_nfe_node(root):
    if root is None:
        return None

    tag = _local_name(root.tag)
    if tag == "NFe":
        return root

    for candidate in root.iter():
        if _local_name(candidate.tag) == "NFe":
            return candidate
    return None


def find_inf_nfe_node(nfe_node):
    if nfe_node is None:
        return None
    for child in nfe_node.iter():
        if _local_name(child.tag) == "infNFe":
            return child
    return None


def nsmap_for(node):
    if node is None:
        return {}
    ns = _namespace_uri(node.tag)
    return {"nfe": ns} if ns else {}


def xpath_text(node, xpath_expr: str, nsmap=None, default: str = ""):
    if node is None:
        return default
    try:
        found = node.xpath(xpath_expr, namespaces=nsmap or {})
    except Exception:
        return default
    if found is None:
        return default

    if isinstance(found, (list, tuple)):
        if not found:
            return default
        if isinstance(found[0], etree._Element):
            return (found[0].text or "").strip() or default
        value = str(found[0]).strip()
        return value or default

    value = str(found).strip()
    return value or default


def extract_chave_from_inf(inf_node):
    if inf_node is None:
        return ""
    ide = inf_node.get("Id", "") or ""
    if ide.startswith("NFe"):
        return ide.replace("NFe", "").strip()
    m = _CHAVE_RE.search(ide)
    return m.group(1) if m else ""


def only_digits(value: str):
    return re.sub(r"\D+", "", value or "")


def _namespace_uri(tag: str):
    if tag.startswith("{") and "}" in tag:
        return tag[1 : tag.index("}")]
    return ""


def _local_name(tag: str):
    if tag.startswith("{") and "}" in tag:
        return tag[tag.index("}") + 1 :]
    return tag
