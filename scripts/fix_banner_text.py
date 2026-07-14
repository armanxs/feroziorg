from pathlib import Path
import re

path = Path(r"D:\Projects\feroziorg\web\index.html")
html = path.read_text(encoding="utf-8")

new_block = """<div class="col-lg-6 col-md-12 col-sm-12 col-xs-12 float-right banner-text">
                                 <h5>His Illustrious Majesty Yusuf-ul-Aulia, Hazart pir Sayyed Feroz Shah Qasimi (Damat Barakatuhumul Aliah)</h5>
                                 <p>
                                    His Illustrious Majesty Yusuf-ul-Aulia, Hazart pir Sayyed Feroz Shah Qasimi (Damat Barakatuhumul Aliah - the most clairvoyant, sacred, religious and spiritual personality) requires no introduction as a successor of devout saints who spent every moment of their lives being lost in the contemplation and rememberance of Allah and His beloved The Holy Prophet (PBUH) Hazart Muhammed (Sallallah-u-alaih-i-wa-alihi-wasallam). The seekers of divinity, mysticism, shariah and the lovers of The Holy Prophet (PBUH) (Sallallah-u-alaih-i-wa-alihi-wasallam) are being imbued with sprituality and bounties (faiz) at Dargha-e-Aaliah Qasimia Ferozia.
                                 </p>
                              </div>"""

pattern = r'<div class="col-lg-6 col-md-12 col-sm-12 col-xs-12 float-right banner-text">.*?</div>'
new_html, n = re.subn(pattern, new_block, html, flags=re.S)
print("replaced", n)
if n < 1:
    raise SystemExit(1)
path.write_text(new_html, encoding="utf-8")
