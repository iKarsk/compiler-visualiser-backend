# Compiler Visualiser Backend

The backend for my lexer and parser visualiser. This repository:

<ul>
<li>Exposes a <a href="https://flask.palletsprojects.com/en/3.0.x/">flask</a> webserver that accepts a program AST, and performs semantic analysis of the AST, generates LLVM IR code for it, and executes the IR with a JIT compiler.</li>

<li>Uses <a href="https://github.com/numba/llvmlite">llvmlite</a> to generate LLVM IR and for JIT compilation. The IR code generation methods for each AST node are visible in `ASTnodes.py`</li>

<li>Containerises compilation and execution of programs with <a href="https://github.com/netblue30/firejail">firejail</a> to prevent resource attacks.</li>
</ul>

# How to run

## Requirements

-   Python3
-   Flask (install using pip3)
-   Firejail (https://github.com/netblue30/firejail)

### How to run

-   cd into the folder containing the backend python server
-   Run server.py

```
$ python3 server.py
```

The output should look something like:

```
* Serving Flask app 'server'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://10.0.0.247:5000
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 956-159-065
```
