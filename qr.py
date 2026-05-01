
#programme por creer un qrcode 
import qrcode

qr = qrcode.QRCode(version=1, box_size=10, border=4)
qr.add_data("93d74d99-280e-46dd-b0c2-37829419f5756")
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.save("qrcode.png")
