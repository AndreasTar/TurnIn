import sshtunnel
import paramiko
import os
import socket
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QGridLayout, QMessageBox, QFileDialog, QInputDialog
from PyQt5 import QtGui, QtCore
from sys import platform, exit

def check_ssh(server_ip, port=22):
    try:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.connect((server_ip, port))
    except Exception as ex:
        # not up, log reason from ex if wanted
        return False
    else:
        test_socket.close()
    return True


class LoginForm(QWidget):
	def __init__(self,host,temp_dir):
		super().__init__()
		self.temp_dir=temp_dir
		self.host=host
		self.setWindowTitle('Login Form')
		self.resize(500, 120)

		layout = QGridLayout()

		label_name = QLabel('<font size="4"> Όνομα Χρήστη </font>')
		self.lineEdit_username = QLineEdit()
		self.lineEdit_username.setPlaceholderText('Παρακαλώ εισάγετε το όνομα χρήστη σας')
		layout.addWidget(label_name, 0, 0)
		layout.addWidget(self.lineEdit_username, 0, 1)

		label_password = QLabel('<font size="4"> Κωδικός Πρόσβασης </font>')
		self.lineEdit_password = QLineEdit()
		self.lineEdit_password.setEchoMode(QLineEdit.Password)
		self.lineEdit_password.setPlaceholderText('Παρακαλώ εισάγετε τον κωδικό πρόσβασή σας')
		layout.addWidget(label_password, 1, 0)
		layout.addWidget(self.lineEdit_password, 1, 1)

		button_login = QPushButton('Είσοδος')
		button_login.setDefault(True)
		button_login.clicked.connect(self.check_password)
		layout.addWidget(button_login, 2, 0, 1, 2)
		layout.setRowMinimumHeight(2, 75)
		self.lineEdit_password.returnPressed.connect(self.check_password)
		self.lineEdit_username.returnPressed.connect(self.check_password)
		self.setLayout(layout)

	def check_password(self):
		msg = QMessageBox()
		username = self.lineEdit_username.text()
		password = self.lineEdit_password.text()
		try:
			ssh = paramiko.SSHClient()
			ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())		
			ssh.connect(proxy, username=username, password=password)
			ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("ruptime")
			servers=ssh_stdout.readlines()
			ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("pwd")
			home_dir=ssh_stdout.readlines()[0][:-1]
			host_to_connect=None
			for server in servers:
				server=server.split()
				host_name=server[0]
				host_is_up=(server[1]=="up")
				if host_is_up and ("opti" in host_name):
					host_to_connect=host_name
					print("{}:is up:{}".format(host_name,host_is_up))
					break
			options = QFileDialog.Options()
			files, _ = QFileDialog.getOpenFileNames(self,"Επιλέξτε τα αρχεία που θέλετε να παραδώσετε", "","All Files (*)", options=options)
			transport = paramiko.Transport((self.host,22))
			transport.connect(None,username,password)
			sftp = paramiko.SFTPClient.from_transport(transport)
			if files:
				remote_dir="{}/{}/".format(home_dir,self.temp_dir)
				print(remote_dir)
				try:
					sftp.mkdir(remote_dir)
				except:
					print("Could not create directory")
				remote_paths=[]
				for localpath in files:
					name=os.path.basename(localpath)
					filepath = "{}{}".format(remote_dir,name)
					try:
						sftp.put(localpath,filepath)
						remote_paths.append(name)
						print("localpath was successfulle uploaded to server")
					except Exception as e:
						print("Could not upload file: "+str(e))
				text, okPressed = QInputDialog.getText(self, "Άσκηση","Ο κωδικός της άσκησης:", QLineEdit.Normal, "")
				if okPressed and text != '':
					turn_in_command="cd {}&&yes|turnin {} {}".format(remote_dir,text, " ".join(remote_paths))
					print(turn_in_command)
					with sshtunnel.open_tunnel(
						(self.host, 22),
						ssh_username=username,
						ssh_password=password,
						remote_bind_address=(host_to_connect, 22),
						local_bind_address=('0.0.0.0', 10022)
					) as tunnel:
						client = paramiko.SSHClient()
						client.load_system_host_keys()
						client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
						client.connect('127.0.0.1', 10022, username=username, password=password)
						ssh_stdin, ssh_stdout, ssh_stderr = client.exec_command(turn_in_command)
						client.exec_command("rm -R {}".format(remote_dir))
						msg.setText("{}\n\n{}".format("".join(ssh_stdout.readlines()),"".join(ssh_stderr.readlines())))
						msg.exec_()
						
						client.close()
			else:
				msg.setText('No Files were selected. Cannot continue with the turn in')
				msg.exec_()
				app.quit()
		except paramiko.AuthenticationException:
			msg.setText('Wrong Password. Please try again')
			msg.exec_()

if __name__ == '__main__':
	if platform == "linux" or platform == "linux2":
		if not os.geteuid() == 0:
			print("only root can run this app")
	proxy="scylla.cs.uoi.gr"
	app = QApplication([])
	form = LoginForm(proxy,"turnin")
	form.show()

	exit(app.exec_())