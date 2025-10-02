#!/usr/bin/env python3
import os
import re

def remove_shell_comments(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Preservar shebang
            if line.startswith('#!'):
                cleaned_lines.append(line)
                continue
            
            # Eliminar comentarios que empiecen con #
            if line.strip().startswith('#'):
                continue
            
            # Eliminar comentarios inline
            if '#' in line:
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
            
            cleaned_lines.append(line)
        
        # Eliminar múltiples líneas vacías consecutivas
        content = '\n'.join(cleaned_lines)
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = content.strip() + '\n'
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Procesado script: {file_path}")
        
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")

def main():
    # Scripts a limpiar (excluyendo scripts de análisis de cache)
    script_files = [
        '/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos/services/data_loader/entrypoint.sh',
        '/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos/quick_check.sh',
        '/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos/download_data.sh',
        '/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos/test_system.sh'
    ]
    
    for file_path in script_files:
        if os.path.exists(file_path):
            remove_shell_comments(file_path)

if __name__ == "__main__":
    main()
