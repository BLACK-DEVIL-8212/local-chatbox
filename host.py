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
        self.conn = None
        self.addr = None
        self.server_socket = None
        self.running = False
        
    def append_message(self, message):
        """Thread-safe method to update chat box"""
        def update():
            current_text = self.ids['ChatBox'].text
            self.ids['ChatBox'].text = current_text + '\n' + message
        Clock.schedule_once(lambda dt: update(), 0)
    
    def clickAction(self):
        """Send message to connected client"""
        if not self.conn:
            self.append_message("[!] No client connected")
            return
            
        textMsg = self.ids['EntryBox'].text.strip()
        if textMsg:
            try:
                self.append_message(f'You: {textMsg}')
                self.ids['EntryBox'].text = ''
                self.conn.sendall(textMsg.encode('utf-8'))
            except (socket.error, BrokenPipeError):
                self.append_message("[!] Failed to send message - client disconnected")
                self.disconnect_client()
    
    def disconnect_client(self):
        """Clean up client connection"""
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None
            self.addr = None
            self.append_message("[!] Client disconnected")
    
    def stop_server(self):
        """Stop the server and clean up"""
        self.running = False
        self.disconnect_client()
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None

class ChatappInterface(App):
    def build(self):
        self.chat = Chat()
        Window.size = (400, 500)
        Window.title = "Local Chat - Host"
        return self.chat
    
    def on_stop(self):
        """Clean up when app closes"""
        if hasattr(self, 'chat'):
            self.chat.stop_server()

def handle_client_messages(chat_instance):
    """Background thread to receive messages from client"""
    while chat_instance.running and chat_instance.conn:
        try:
            chat_instance.conn.settimeout(1.0)
            data = chat_instance.conn.recv(4096)
            if not data:
                chat_instance.append_message("[!] Client has disconnected")
                break
                
            message = data.decode('utf-8')
            chat_instance.append_message(f'Client: {message}')
            
        except socket.timeout:
            continue  # Normal timeout, keep listening
        except socket.error as e:
            if chat_instance.running:
                chat_instance.append_message(f"[!] Connection error: {str(e)}")
            break
        except Exception as e:
            if chat_instance.running:
                chat_instance.append_message(f"[!] Error receiving message: {str(e)}")
            break
    
    chat_instance.disconnect_client()

def start_host_server(chat_instance, host, port):
    """Start the host server and accept connections"""
    try:
        # Create and configure server socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(1)
        server_socket.settimeout(1.0)
        
        chat_instance.server_socket = server_socket
        chat_instance.running = True
        chat_instance.append_message(f"[+] Server started on {host}:{port}")
        chat_instance.append_message("[+] Waiting for client connection...")
        
        # Wait for client connection
        while chat_instance.running:
            try:
                conn, addr = server_socket.accept()
                chat_instance.conn = conn
                chat_instance.addr = addr
                chat_instance.append_message(f"[+] Connected with client: {addr[0]}:{addr[1]}")
                
                # Start receiving thread for this client
                receive_thread = threading.Thread(
                    target=handle_client_messages,
                    args=(chat_instance,),
                    daemon=True
                )
                receive_thread.start()
                break  # Exit waiting loop once connected
                
            except socket.timeout:
                continue  # Normal timeout, keep waiting
            except Exception as e:
                if chat_instance.running:
                    chat_instance.append_message(f"[!] Error accepting connection: {str(e)}")
                break
                
    except socket.error as e:
        chat_instance.append_message(f"[!] Failed to start server: {str(e)}")
        if "Address already in use" in str(e):
            chat_instance.append_message(f"[!] Port {port} is already in use")
        chat_instance.running = False
    except Exception as e:
        chat_instance.append_message(f"[!] Unexpected error: {str(e)}")
        chat_instance.running = False
    finally:
        if not chat_instance.running:
            chat_instance.stop_server()

def validate_ip(host):
    """Validate IP address format"""
    if host == "0.0.0.0" or host == "localhost":
        return True
    
    parts = host.split('.')
    if len(parts) != 4:
        return False
    
    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except ValueError:
        return False

def main():
    """Main entry point with input validation"""
    # Get host IP with validation
    while True:
        host = input("Enter your IP address (0.0.0.0 for all interfaces, or specific IP): ").strip()
        if not host:
            print("IP address cannot be empty")
            continue
        
        if host == "0.0.0.0":
            print("[+] Listening on all network interfaces")
            break
        elif host.lower() == "localhost":
            host = "127.0.0.1"
            break
        elif validate_ip(host):
            break
        else:
            print("Invalid IP address format. Use format: xxx.xxx.xxx.xxx")
    
    port = 4444
    
    # Start the chat application
    chat_app = ChatappInterface()
    
    # Start server thread
    server_thread = threading.Thread(
        target=start_host_server,
        args=(chat_app.chat, host, port),
        daemon=True
    )
    server_thread.start()
    
    # Run the Kivy app
    chat_app.run()

if __name__ == "__main__":
    main()
