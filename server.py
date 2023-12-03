from flask import Flask, request, jsonify
import subprocess
import random
import string
import os


app = Flask(__name__)

def compile_file(filename):
	result = subprocess.run(['gcc', "./userCode/" + filename + ".c", '-o', "./userCode/" + filename], stderr=subprocess.PIPE)
	string_output = result.stderr.decode('utf-8')
	return (result.returncode, string_output)

def run_file(filename):
	result = subprocess.run(['firejail', './userCode/' + filename], stdout=subprocess.PIPE).stdout.decode('utf-8')
	return result

@app.route('/')
def index():
	return "hello world"



# Get random string of 10 characters length
def get_random_string():
	letters = string.ascii_letters
	result_str = ''.join(random.choice(letters) for i in range(10))
	return result_str


@app.route('/compile', methods=["POST"])
def command_server():
	if request.is_json:
		data = request.json
		code = data.get("code")

		while True:
			filename = get_random_string()
			exists = os.path.isfile('./userCode/' + filename + ".c")
			if not exists:
				break

		f = open("./userCode/" + filename + ".c", "w")
		f.write(code)
		f.close()


		compile_result = compile_file(filename)
		if compile_result[0] != 0:
			terminal_output = compile_result[1].replace("./userCode/" + filename + ".c", "./program.c")
			os.remove("./userCode/" + filename + ".c")
			return {
			"success": False,
			"result" : terminal_output
			}
		else:
			run_result = run_file(filename)
			os.remove("./userCode/" + filename)
			os.remove("./userCode/" + filename + ".c")
			return {
			"success": True,
			"result": run_result
			}
	else:
		return "Content type not supported"

if __name__ == "__main__":
	app.run(host="0.0.0.0", port=int("5000"), debug=True)

