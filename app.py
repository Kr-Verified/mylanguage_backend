from flask import Flask, request, jsonify
import re
import subprocess
import os

app = Flask(__name__)

def lexer(source_code):
    tokens = []
    lines = source_code.split("\n")

    for line in lines:
        line = line.strip()

        #변수 할당
        if match := re.match(r"변수 (\w+) = (.+)", line):
            var_name, value = match.groups()
            tokens.append(("ASSIGN", var_name, value.strip('"')))

        # 변수 재할당
        elif match := re.match(r"(\w+) = (.+)", line):
            var_name, value = match.groups()
            tokens.append(("ASSIGN", var_name, value))

        #출력
        elif match := re.match(r"출력\((\w+|\".*\")\)", line):
            tokens.append(("PRINT", match.group(1)))

        #조건문
        elif match := re.match(r"만약\((.+)\) {", line):
            tokens.append(("IF", match.group(1)))

        #반복문
        elif match := re.match(r"반복\((.+)\)", line):
            tokens.append(("WHILE", match.group(1)))

        #종료
        elif line == "}":
            tokens.append(("BLOCK_END",))
        
    return tokens

def transpile_to_c(tokens):
    c_code = [
        "#include<stdio.h>",
        '#include <stdlib.h>',
        '#include <string.h>',
        '',
        'typedef struct {',
        '    int type;  // 0 = int, 1 = string',
        '    union {',
        '        int int_value;',
        '        char* str_value;',
        '    };',
        '} Value;',
        '',
        'void print(Value v) {',
        '    if (v.type == 0) {',
        '        printf("%d\\n", v.int_value);',
        '    }else {',
        '        printf("%s\\n", v.str_value);',
        '    }',
        '}',
        '',
        'int main() {'
    ]
    variables = {}

    for token in tokens:
        if token[0] == "ASSIGN":
            var_name, value = token[1], token[2]
            if value.isdigit():
                variables[var_name] = "int"
                c_code.append(f'    Value {var_name} = {{ .type = 0, .int_value = {value} }};')
            else:
                variables[var_name] = "string"
                c_code.append(f'    Value {var_name} = {{ .type = 1, .str_value = strdup("{value}") }};')

        elif token[0] == "PRINT":
            var_name = token[1]
            if var_name.startswith('"'):
                c_code.append(f'    print((Value){{ .type = 1, .str_value = {var_name} }});')
            else:
                c_code.append(f'    print({var_name});')

        elif token[0] == "IF":
            condition = token[1].replace("=", "==")
            c_code.append(f'    if ({condition}) {{')
        
        elif token[0] == "WHILE":
            condition = token[1].replace("=", "==")
            c_code.append(f'    while ({condition}) {{')

        elif token[0] == "BLOCK_END":
            c_code.append("    }")

    c_code.append('    return 0;\n}')
    return "\n".join(c_code)

def compile_and_run(c_code):
    c_file = "temp.c"
    exe_file = "temp.exe" if os.name == "nt" else "./temp.out"

    #c 코드 저장
    with open(c_file, "w", encoding="utf-8") as f:
        f.write(c_code)

    #GCC로 컴파일
    compile_result = subprocess.run(["gcc", c_file, "-o", exe_file], capture_output=True, text=True)
    if compile_result.returncode != 0:
        return "컴파일 오류:\n" + compile_result.stderr

    #실행
    run_result = subprocess.run([exe_file], capture_output=True, text=True)
    return run_result.stdout

@app.route("/run", methods=["POST"])
def run():
    data = request.json
    source_code = data.get("code", "")

    tokens = lexer(source_code)
    c_code = transpile_to_c(tokens)
    output = compile_and_run(c_code)

    return jsonify({"output": output})

if __name__ == "__main__":
    app.run(debug=True)