from fastapi import APIRouter, Depends, HTTPException

from app import nginx_conf
from app.deps import require_super_admin
from app.models import Admin
from app.schemas import NginxDomainIn, NginxStatusOut

router = APIRouter(prefix="/api/admin/nginx", tags=["nginx"])


@router.get("", response_model=NginxStatusOut)
def get_status(_: Admin = Depends(require_super_admin)):
    return NginxStatusOut(**nginx_conf.status())


@router.post("/install", response_model=NginxStatusOut)
def install_nginx(_: Admin = Depends(require_super_admin)):
    ok, msg = nginx_conf.install_nginx()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return NginxStatusOut(**nginx_conf.status())


@router.post("/domains", response_model=NginxStatusOut)
def add_domain(payload: NginxDomainIn, _: Admin = Depends(require_super_admin)):
    ok, msg = nginx_conf.add_domain(payload.domain, payload.ssl_cert, payload.ssl_key)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return NginxStatusOut(**nginx_conf.status())


@router.delete("/domains/{domain}", response_model=NginxStatusOut)
def remove_domain(domain: str, _: Admin = Depends(require_super_admin)):
    ok, msg = nginx_conf.remove_domain(domain)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return NginxStatusOut(**nginx_conf.status())
