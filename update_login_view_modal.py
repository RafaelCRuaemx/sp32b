import re

with open("/home/rafael/desarrollo/benitto_proyecto/fontend/src/views/LoginView.jsx", "r") as f:
    content = f.read()

content = content.replace("email={email}", "email={email}\n        tempToken={tempToken}")

with open("/home/rafael/desarrollo/benitto_proyecto/fontend/src/views/LoginView.jsx", "w") as f:
    f.write(content)
