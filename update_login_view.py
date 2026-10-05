with open("/home/rafael/desarrollo/benitto_proyecto/fontend/src/views/LoginView.jsx", "r") as f:
    content = f.read()

replacement = """      if (res.status === '2fa_required') {
        setTempUser(res.user);
        setTempToken(res.tempToken);
        setStep(2);
        setTimeout(() => pinInputRefs.current[0]?.focus(), 150);
      } else if (res.status === 'setup_2fa_required') {
        setTempUser(res.user);
        setTempToken(res.tempToken);
        setStep(2);
        setShowQrModal(true);
        setTimeout(() => pinInputRefs.current[0]?.focus(), 150);
"""

content = content.replace("      if (res.status === '2fa_required') {", replacement)

with open("/home/rafael/desarrollo/benitto_proyecto/fontend/src/views/LoginView.jsx", "w") as f:
    f.write(content)
