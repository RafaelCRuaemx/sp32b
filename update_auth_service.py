with open("/home/rafael/desarrollo/benitto_proyecto/fontend/src/services/authService.js", "r") as f:
    content = f.read()

new_method = """
  setup2FAReal: async (tempToken) => {
    const response = await fetch('/api/auth/setup-2fa/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ temp_token: tempToken }),
    });
    if (!response.ok) throw new Error('Error al generar QR');
    return await response.json();
  },
"""
content = content.replace("logout: () => {", new_method + "  logout: () => {")

with open("/home/rafael/desarrollo/benitto_proyecto/fontend/src/services/authService.js", "w") as f:
    f.write(content)
