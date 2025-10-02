#!/usr/bin/env python3
import os
import re

def remove_comments(file_path, skip_files=None):
    if skip_files and any(skip in file_path for skip in skip_files):
        print(f"Saltando archivo de análisis: {file_path}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Guardar shebang si existe
        shebang = ""
        if content.startswith('#!'):
            lines = content.split('\n', 1)
            shebang = lines[0] + '\n'
            content = lines[1] if len(lines) > 1 else ""
        
        # Eliminar docstrings de módulo (al inicio del archivo)
        content = re.sub(r'^""".*?"""', '', content, flags=re.DOTALL | re.MULTILINE)
        content = re.sub(r"^'''.*?'''", '', content, flags=re.DOTALL | re.MULTILINE)
        
        # Eliminar docstrings de funciones y clases
        content = re.sub(r'(\n\s+)""".*?"""', r'\1', content, flags=re.DOTALL)
        content = re.sub(r"(\n\s+)'''.*?'''", r'\1', content, flags=re.DOTALL)
        
        # Eliminar comentarios inline (# comentario)
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Preservar líneas con solo imports o código importante
            # Eliminar comentarios que empiecen con #
            if '#' in line and not line.strip().startswith('#!'):
                # Buscar # que no esté dentro de strings
                in_string = False
                quote_char = None
                for i, char in enumerate(line):
                    if char in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
                        if not in_string:
                            in_string = True
                            quote_char = char
                        elif char == quote_char:
                            in_string = False
                            quote_char = None
                    elif char == '#' and not in_string:
                        line = line[:i].rstrip()
                        break
            
            # Solo agregar líneas que no sean comentarios puros
            if line.strip() and not line.strip().startswith('#'):
                cleaned_lines.append(line)
            elif not line.strip():  # Preservar líneas vacías
                cleaned_lines.append(line)
        
        # Reconstruir contenido
        content = '\n'.join(cleaned_lines)
        
        # Eliminar múltiples líneas vacías consecutivas
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Agregar shebang de vuelta si existía
        if shebang:
            content = shebang + content
        
        # Limpiar espacios al final
        content = content.strip() + '\n'
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Procesado: {file_path}")
        
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")

def main():
    # Archivos a saltar (scripts de análisis de cache)
    skip_files = [
        'simple_cache_analysis.py',
        'generate_cache_analysis.py', 
        'analyze_cache.py'
    ]
    
    # Procesar todos los archivos Python en services/
    services_dir = '/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos/services'
    
    for root, dirs, files in os.walk(services_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                remove_comments(file_path, skip_files)

if __name__ == "__main__":
    main()
