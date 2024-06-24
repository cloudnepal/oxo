"""export utils module: contains utility functions to export the scan details."""

import io
import ipaddress
import json
import pathlib
import zipfile

from ostorlab.runtimes.local.models import models
from ostorlab.serve_app import common

SCAN_JSON = "scan.json"
ASSET_JSON = "asset.json"
VULNERABILITY_JSON = "vulnerability.json"

RISK_RATINGS_ORDER = {
    common.RiskRatingEnum.CRITICAL.name: 8,
    common.RiskRatingEnum.HIGH.name: 7,
    common.RiskRatingEnum.MEDIUM.name: 6,
    common.RiskRatingEnum.LOW.name: 5,
    common.RiskRatingEnum.POTENTIALLY.name: 4,
    common.RiskRatingEnum.HARDENING.name: 3,
    common.RiskRatingEnum.SECURE.name: 2,
    common.RiskRatingEnum.IMPORTANT.name: 1,
    common.RiskRatingEnum.INFO.name: 0,
}


def export_scan(scan: models.Scan, export_ide: bool = False) -> bytes:
    """Export the scan details from the given file data.

    Args:
        scan: The scan object.
        export_ide: Whether to export the IDE or not.
    """
    fd = io.BytesIO()
    archive = zipfile.ZipFile(fd, "a", zipfile.ZIP_DEFLATED, True)

    _export_asset(scan.id, archive)
    _export_scan(scan, archive)
    _export_vulnz(scan.id, archive)

    if export_ide is True:
        raise NotImplementedError()

    archive.close()
    fd.seek(0)
    return fd.read()


def _export_asset(scan_id: int, archive: zipfile.ZipFile) -> None:
    """Export the asset details to the given archive.

    Args:
        scan_id: The scan id.
        archive: The archive object.
    """

    with models.Database() as session:
        assets = (
            session.query(models.Asset).filter(models.Asset.scan_id == scan_id).all()
        )
        if len(assets) == 0:
            return None
        assets_data = []
        for asset in assets:
            asset_type = (
                asset.type.replace("_", " ").lower()
                if "_" in asset.type
                else asset.type
            )
            asset_dict = {
                "tags": None,
                "type": asset_type.lower(),
            }
            if asset.type == "android_file":
                if asset.path is not None:
                    mobile_app = pathlib.Path(asset.path).name
                    asset_dict["path"] = mobile_app
                    android_file_asset_path = pathlib.Path(asset.path)
                    if android_file_asset_path.exists() is False:
                        raise ValueError(f"Android File {asset.path} not found.")
                    try:
                        archive.writestr(
                            mobile_app, android_file_asset_path.read_bytes()
                        )
                    except Exception:
                        pass

            elif asset.type == "ios_file":
                if asset.path is not None:
                    mobile_app = pathlib.Path(asset.path).name
                    asset_dict["path"] = mobile_app
                    ios_file_asset_path = pathlib.Path(asset.path)
                    if ios_file_asset_path.exists() is False:
                        raise ValueError(f"IOS File {asset.path} not found.")
                    try:
                        archive.writestr(mobile_app, ios_file_asset_path.read_bytes())
                    except Exception:
                        pass
            elif asset.type == "android_store":
                asset_dict["package_name"] = asset.package_name
                asset_dict["application_name"] = asset.application_name
            elif asset.type == "ios_store":
                asset_dict["package_name"] = asset.bundle_id
                asset_dict["application_name"] = asset.application_name
            elif asset.type == "network":
                networks = []
                ips = (
                    session.query(models.IPRange)
                    .filter(models.IPRange.network_asset_id == asset.id)
                    .all()
                )
                for ip in ips:
                    ip_network = ipaddress.ip_network(ip.host, strict=False)
                    networks.append(
                        f"{ip_network.network_address.exploded}/{ip_network.prefixlen}"
                    )
                asset_dict["networks"] = networks
            elif asset.type == "urls":
                urls = []
                links = (
                    session.query(models.Link)
                    .filter(models.Link.urls_asset_id == asset.id)
                    .all()
                )
                for link in links:
                    urls.append(link.url)
                asset_dict["urls"] = urls
            else:
                raise NotImplementedError()

            assets_data.append(asset_dict)

        assets_data = "\n".join([json.dumps(asset) for asset in assets_data])
        archive.writestr(ASSET_JSON, assets_data)


def _export_scan(scan: models.Scan, archive: zipfile.ZipFile) -> None:
    """Export the scan details to the given archive.

    Args:
        scan: The scan object.
        archive: The archive object.
    """

    scan_dict = {
        "title": scan.title,
        "created_time": scan.created_time.strftime("%Y-%m-%d %H:%M:%S"),
        "risk_rating": _compute_risk_rating(scan_id=scan.id),
        "status": [],
    }

    with models.Database() as session:
        scan_statuses = (
            session.query(models.ScanStatus)
            .filter(models.ScanStatus.scan_id == scan.id)
            .all()
        )
        for status in scan_statuses:
            scan_dict["status"].append(
                {
                    "id": status.id,
                    "key": status.key,
                    "value": status.value,
                }
            )
        archive.writestr(SCAN_JSON, json.dumps(scan_dict))


def _export_vulnz(scan_id: int, archive: zipfile.ZipFile) -> None:
    """Export the vulnerabilities details to the given archive.

    Args:
        scan_id: The scan id.
        archive: The archive object.
    """

    with models.Database() as session:
        vulns_list = []
        vulnerabilities = session.query(models.Vulnerability).filter(
            models.Vulnerability.scan_id == scan_id
        )
        for vuln in vulnerabilities:
            references = (
                session.query(models.Reference)
                .filter(models.Reference.vulnerability_id == vuln.id)
                .all()
            )
            refs_list = [{"title": ref.title, "url": ref.url} for ref in references]
            kb_dict = {
                "title": vuln.title,
                "short_description": vuln.short_description,
                "description": vuln.description,
                "recommendation": vuln.recommendation,
                "risk_rating": vuln.risk_rating.name.lower(),
                "references": refs_list,
            }

            vulns_list.append(
                {
                    "detail": kb_dict,
                    "technical_detail": vuln.technical_detail,
                    "risk_rating": vuln.risk_rating.name.lower(),
                    "cvss_v3_vector": vuln.cvss_v3_vector,
                }
            )
        archive.writestr(VULNERABILITY_JSON, json.dumps(vulns_list))


def _compute_risk_rating(scan_id: int) -> str:
    """Compute the risk rating for the given scan id.

    Args:
        scan_id: The scan id.
    """

    with models.Database() as session:
        scan = session.query(models.Scan).filter(models.Scan.id == scan_id).first()
        if scan is None:
            return "unknown"

        vulnerabilities = session.query(models.Vulnerability).filter(
            models.Vulnerability.scan_id == scan_id
        )
        distinct_vulnz = vulnerabilities.distinct(
            models.Vulnerability.risk_rating,
        ).all()

        if len(distinct_vulnz) == 0:
            return "unknown"

        vuln_highest_risk = max(
            distinct_vulnz,
            key=lambda vuln: RISK_RATINGS_ORDER[vuln.risk_rating.name],
        )
        scan_risk_rating = vuln_highest_risk.risk_rating.name.lower()
        return scan_risk_rating
