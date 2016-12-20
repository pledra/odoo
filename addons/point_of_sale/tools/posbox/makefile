DEVICE ?=sdc
ODOO_CLONE=overwrite_before_init/home/pi/odoo
.RECIPEPREFIX= >
DIST_REPO ?= file:///home/odoo/devel/posbox/odoo
BRANCH ?= 8.0-pos-new-impl-display-lpe
MOUNT_POINT = root_mount/

clone: odoo
>cd $(ODOO_CLONE)/.. && git clone -b $(BRANCH) --no-local --no-checkout --depth 1 $(DIST_REPO) 2> /dev/null

pull: clone
>cd $(ODOO_CLONE) && git pull $(DIST_REPO) $(BRANCH)

sparse-co: clone
>cd $(ODOO_CLONE) && git config core.sparsecheckout true && \
echo "addons/web \
addons/web_kanban \
addons/hw_* \
addons/point_of_sale/tools/posbox/configuration \
openerp/ \
odoo.py" | tee --append .git/info/sparse-checkout > /dev/null && \
git read-tree -mu HEAD
 
odoo:
>test -d $(ODOO_CLONE) || mkdir $(ODOO_CLONE)

dd: posbox-inited.img
>sudo dd if=posbox-inited.img of=/dev/$(DEVICE) bs=4M status=progress

raspbian.img: 
>wget 'https://downloads.raspberrypi.org/raspbian_lite_latest' -O raspbian.img.zip
>unzip raspbian.img.zip

kernel-qemu:
>wget 'https://github.com/dhruvvyas90/qemu-rpi-kernel/raw/master/kernel-qemu-4.1.13-jessie' -O kernel-qemu

posbox.img: raspbian.img
>cp -a raspbian.img posbox.img
>dd if=/dev/zero bs=1M count=2048 >> posbox.img

fdisking: posbox.img
>START_OF_ROOT_PARTITION=$(fdisk -l posbox.img | tail -n 1 | awk '{print $2}')
>(echo 'p';                          # print \
 echo 'd';                           # delete \
 echo '2';                           #   second partition \
 echo 'n';                          # create new partition \ 
 echo 'p';                         #   primary \
 echo '2';                          #   number 2 \
 echo "${START_OF_ROOT_PARTITION}";  #   starting at previous offset \
 echo '';                            #   ending at default (fdisk should propose max) \
 echo 'p';                           # print \
 echo 'w') | fdisk posbox.img       # write and quit \
>e2fsck -f "${LOOP_MAPPER_PATH}" # resize2fs requires clean fs
>make loop-mapper-path
>resize2fs "${LOOP_MAPPER_PATH}"

before-init:loop-mapper-path fdisking
>mkdir "${MOUNT_POINT}" 2> /dev/null
>mount "${LOOP_MAPPER_PATH}" "${MOUNT_POINT}"
>cp -av overwrite_before_init/ ${MOUNT_POINT}
>umount $MOUNT_POINT

init: kernel-qemu
>QEMU_OPTS=(-kernel kernel-qemu -cpu arm1176 -m 256 -M versatilepb -no-reboot -serial stdio -append 'root=/dev/sda2 rootfstype=ext4 rw' -hda posbox.img -net user,hostfwd=tcp::10022-:22,hostfwd=tcp::18069-:8069 -net nic)
>qemu-system-arm "${QEMU_OPTS[@]}"

after-init:
>mount "${LOOP_MAPPER_PATH}" "${MOUNT_POINT}"
>cp -av "${OVERWRITE_FILES_AFTER_INIT_DIR}"/* "${MOUNT_POINT}"
>umount $MOUNT_POINT

zerofree:loop-mapper-path
>zerofree -v "${LOOP_MAPPER_PATH}" || true

loop-mapper-path:
>LOOP_MAPPER_PATH := $(kpartx -avs posbox.img | tail -n 1 | cut -d ' ' -f 3)
>LOOP_MAPPER_PATH := "/dev/mapper/${LOOP_MAPPER_PATH}"

.PHONY: sequence clean zerofree *init fdisking clone pull sparse-co odoo dd

sequence: | sparse-co before-init init after-init zerofree

clean:
>rm -Rf $(ODOO_CLONE)
>rm -Rf $(MOUNT_POINT)
>rm posbox.img