import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sys
import os
import re

# Redirigir stdout a la caja de texto
class TextRedirector(object):
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, str, (self.tag,))
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")
        
    def flush(self):
        pass

class AppSEO:
    def __init__(self, root):
        self.root = root
        self.root.title("Cazucá Optimización")
        self.root.geometry("800x700")
        self.root.configure(padx=20, pady=20)
        
        # Verificar API Key
        from dotenv import load_dotenv
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
        
        self.crear_interfaz()
        
        if not self.api_key:
            messagebox.showwarning("Falta API Key", "No se encontró GROQ_API_KEY en el archivo .env. Asegúrate de configurarlo antes de optimizar.")

    def crear_interfaz(self):
        # Título principal
        lbl_titulo = tk.Label(self.root, text="Cazucá Optimización", font=("Helvetica", 16, "bold"))
        lbl_titulo.pack(anchor="w", pady=(0, 2))
        
        lbl_slogan = tk.Label(self.root, text="Por unas notas con más apuñaladas para SEO", font=("Helvetica", 9, "italic"), fg="gray")
        lbl_slogan.pack(anchor="w", pady=(0, 10))
        
        # Frame superior (Texto y Keyword)
        frame_top = tk.Frame(self.root)
        frame_top.pack(fill=tk.BOTH, expand=True)
        
        # Texto de la noticia
        lbl_noticia = tk.Label(frame_top, text="1. Pega el texto de la noticia aquí:", font=("Helvetica", 10, "bold"))
        lbl_noticia.pack(anchor="w")
        
        self.txt_noticia = scrolledtext.ScrolledText(frame_top, height=15, wrap=tk.WORD)
        self.txt_noticia.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Frame de inputs pequeños
        frame_inputs = tk.Frame(frame_top)
        frame_inputs.pack(fill=tk.X, pady=(0, 15))
        
        # Título Corto (para nombre de carpeta)
        lbl_slug = tk.Label(frame_inputs, text="Título corto (para la carpeta):", font=("Helvetica", 10))
        lbl_slug.grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        self.ent_slug = tk.Entry(frame_inputs, width=50)
        self.ent_slug.grid(row=0, column=1, sticky="w", padx=(0, 20))
        self.ent_slug.insert(0, "noticia-nueva")
        
        # Botón Optimizar
        self.btn_optimizar = tk.Button(self.root, text="🚀 INICIAR OPTIMIZACIÓN SEO", font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", cursor="hand2", command=self.iniciar_optimizacion_thread)
        self.btn_optimizar.pack(fill=tk.X, pady=10)
        
        # Log Output
        lbl_log = tk.Label(self.root, text="Consola de Trabajo (Progreso del Equipo):", font=("Helvetica", 10, "bold"))
        lbl_log.pack(anchor="w")
        
        self.txt_log = scrolledtext.ScrolledText(self.root, height=10, bg="black", fg="#00FF00", font=("Consolas", 10))
        self.txt_log.pack(fill=tk.BOTH, expand=True)
        self.txt_log.configure(state="disabled")
        
        # Redirigir consola a la GUI
        sys.stdout = TextRedirector(self.txt_log, "stdout")
        sys.stderr = TextRedirector(self.txt_log, "stderr")

    def limpiar_slug(self, texto):
        texto = texto.lower()
        texto = re.sub(r'[^a-z0-9]+', '-', texto)
        return texto.strip('-')[:50]

    def iniciar_optimizacion_thread(self):
        texto = self.txt_noticia.get("1.0", tk.END).strip()
        slug_raw = self.ent_slug.get().strip()
        
        if not texto:
            messagebox.showerror("Error", "Por favor pega el texto de la noticia.")
            return
        if not slug_raw:
            messagebox.showerror("Error", "Por favor escribe un título corto para la carpeta.")
            return
            
        slug = self.limpiar_slug(slug_raw)
        
        self.btn_optimizar.config(state="disabled", text="⏳ OPTIMIZANDO... (Por favor espera)")
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", tk.END)
        self.txt_log.configure(state="disabled")
        
        # Correr en un hilo separado para no congelar la GUI
        hilo = threading.Thread(target=self.proceso_optimizacion, args=(texto, slug))
        hilo.daemon = True
        hilo.start()

    def proceso_optimizacion(self, texto, slug):
        try:
            # Importar de nuestro código existente
            from optimizar import ejecutar_optimizacion
            out_path = ejecutar_optimizacion(texto, slug)
            
            # Mostrar mensaje de éxito
            self.root.after(0, lambda: messagebox.showinfo("¡Éxito!", f"Proceso finalizado. Archivo guardado en:\n{out_path}"))
            
            # Abrir la carpeta contenedora en Windows
            os.startfile(os.path.dirname(out_path))
            
        except Exception as e:
            print(f"\\n❌ ERROR FATAL: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Ocurrió un error durante la optimización:\\n{str(e)}"))
        finally:
            self.root.after(0, lambda: self.btn_optimizar.config(state="normal", text="🚀 INICIAR OPTIMIZACIÓN SEO"))

if __name__ == "__main__":
    root = tk.Tk()
    app = AppSEO(root)
    root.mainloop()
