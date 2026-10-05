with open("/home/rafael/desarrollo/benitto_proyecto/fontend/src/components/QrEnrollModal.jsx", "r") as f:
    content = f.read()

replacement = """import React, { useState, useEffect } from 'react';
import { authService } from '../services/authService';
import { XMarkIcon } from '@heroicons/react/24/outline';

export default function QrEnrollModal({ email, tempToken, isOpen, onClose }) {
  const [copied, setCopied] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && tempToken && !data) {
      setLoading(true);
      authService.setup2FAReal(tempToken)
        .then(res => setData(res))
        .catch(err => console.error(err))
        .finally(() => setLoading(false));
    } else if (isOpen && !tempToken && !data) {
        // Fallback for mock mode or manual trigger without token
        setData(authService.setup2FA(email || 'admin@escuela.edu'));
    }
  }, [isOpen, tempToken, data, email]);

  if (!isOpen) return null;

  const handleCopy = () => {
    if(!data) return;
    navigator.clipboard.writeText(data.secret);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
"""

content = content.split("  if (!isOpen) return null;")[1]
content = content.split("  const data = authService.setup2FA(email || 'admin@escuela.edu');")[1]

# Need to conditionally render body if data is null
body_replacement = """
        <div className="py-4 space-y-4">
          {loading || !data ? (
              <div className="text-center p-4 text-sm text-slate-500">Cargando código seguro...</div>
          ) : (
            <>
          {/* Imagen del Código QR */}
          <div className="flex flex-col items-center justify-center p-3 bg-slate-50 rounded-xl border border-slate-200">
            <img
              src={data.qrImageUrl}
              alt="Código QR Google Authenticator"
              className="w-48 h-48 rounded-lg shadow-xs bg-white p-1"
            />
            <p className="text-[11px] text-slate-500 mt-2 text-center">
              Abre <strong>Google Authenticator</strong> en tu teléfono, pulsa <strong>(+)</strong> y selecciona <strong>Escanear código QR</strong>.
            </p>
          </div>

          {/* Clave Manual Base32 */}
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs">
            <span className="text-slate-500 font-medium block mb-1">¿No puedes escanear el QR? Usa esta clave:</span>
            <div className="flex items-center justify-between bg-white px-2.5 py-1.5 rounded-lg border border-slate-300 font-mono font-bold text-slate-800 tracking-wider">
              <span>{data.secret}</span>
              <button
                type="button"
                onClick={handleCopy}
                className="text-[11px] px-2 py-0.5 rounded theme-btn-primary cursor-pointer transition-all"
              >
                {copied ? '¡Copiado!' : 'Copiar'}
              </button>
            </div>
          </div>
          </>
          )}
        </div>
"""

final_code = replacement + "\n" + content
final_code = final_code.replace("        <div className=\"py-4 space-y-4\">", body_replacement).split("          {/* Imagen del Código QR */}")[0] + body_replacement.split("          {/* Imagen del Código QR */}")[1]

# Remove the old backup codes block because backend doesn't send it yet (unless we mock it).
# The split trick might be messy. Let's just do a clean rewrite of the component body.
