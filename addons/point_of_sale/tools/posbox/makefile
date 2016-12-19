DEVICE?=sdc
ODOO_CLONE=overwrite_before_init/home/pi/odoo

repo: odoo;
    cd $(ODOO_CLONE) && git clone -b 8.0-pos-new-impl-display-lpe --no-local --no-checkout --depth 1 file:///home/odoo/devel/posbox/odoo && \
    git config core.sparsecheckout true && \
    echo "addons/web
addons/web_kanban
addons/hw_*
addons/point_of_sale/tools/posbox/configuration
openerp/
odoo.py" | tee --append .git/info/sparse-checkout > /dev/null && \
    git read-tree -mu HEAD ;

odoo:
    mkdir $(ODOO_CLONE)

dd: posbox-inited.img;
    sudo dd if=posbox-inited.img of=/dev/$(DEVICE) bs=4M status=progress
