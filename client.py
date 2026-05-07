import threading
import socket
import sys
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.clock import Clock

class Chat(BoxLayout):
    
    def __init__(self, **kwargs):
        super(Chat, self).__init__(**kwargs)
        self.socket = None
        self.running = False
        
    def append_message(self, message):
        """Thread-safe method to update chat box"""
        def update():
            current_text = self.ids['ChatBox'].text
            self.ids['ChatBox'].text = current_text + '\n' + message
        Clock.schedule_once(lambda dt: update(), 0)
    
    def clickAction(self):
        """Send message to connected peer"""
        if not self.socket:
            self.append_message("[!] Not connected to any peer")
            return
            
        textMsg = self.ids['EntryBox'].text.strip()
        if textMsg:
            try:
                self.append_message(f'You: {textMsg}')
                self.ids['EntryBox'].text = ''
                self.socket.sendall(textMsg.encode('utf-8'))
            except (socket.error, BrokenPipeError):
                self.append_message("[!] Failed to send message - connection lost")
                self.disconnect()
    
    def disconnect(self):
        """Clean up connection"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

class ChatAppInterface(App):
    def build(self):
        self.chat = Chat()
        Window.size = (400, 500)
        Window.title = "Local Chat - Client"
        return self.chat
    
    def on_stop(self):
        """Clean up when app closes"""
        if hasattr(self, 'chat'):
            self.chat.disconnect()

def receive_messages(chat_instance, host, port):
    """Background thread to receive messages from host"""
    try:
        # Create socket and connect
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5.0)  # Timeout for connection
        client_socket.connect((host, port))
        
        chat_instance.socket = client_socket
        chat_instance.running = True
        chat_instance.append_message("[+] Successfully connected to host")
        
        while chat_instance.running:
            try:
                client_socket.settimeout(1.0)  # Timeout for recv
                data = client_socket.recv(4096)
                if not data:
                    chat_instance.append_message("[!] Host has disconnected")
                    break
                    
                message = data.decode('utf-8')
                chat_instance.append_message(f'Host: {message}')
                
            except socket.timeout:
                continue  # Normal timeout, keep listening
            except socket.error as e:
                if chat_instance.running:
                    chat_instance.append_message(f"[!] Connection error: {str(e)}")
                break
                
    except socket.gaierror:
        chat_instance.append_message(f"[!] Invalid host address: {host}")
    except socket.timeout:
        chat_instance.append_message("[!] Connection timeout - host not responding")
    except ConnectionRefusedError:
        chat_instance.append_message("[!] Connection refused - is the host running?")
    except Exception as e:
        chat_instance.append_message(f"[!] Unable to connect: {str(e)}")
    finally:
        chat_instance.disconnect()

def main():
    """Main entry point with input validation"""
    # Get host IP with validation
    while True:
        host = input("Enter host IP address (e.g., 192.168.1.100): ").strip()
        if not host:
            print("IP address cannot be empty")
            continue
            
        # Basic IP validation
        parts = host.split('.')
        if len(parts) == 4:
            try:
                valid = all(0 <= int(part) <= 255 for part in parts)
                if valid:
                    break
            except ValueError:
                pass
        print("Invalid IP address format. Please use format: xxx.xxx.xxx.xxx")
    
    port = 4444
    
    # Start the chat application
    chat_app = ChatAppInterface()
    
    # Start receiving thread
    receive_thread = threading.Thread(
        target=receive_messages,
        args=(chat_app.chat, host, port),
        daemon=True
    )
    receive_thread.start()
    
    # Run the Kivy app
    chat_app.run()

if __name__ == '__main__':
    main()
