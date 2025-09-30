from .serialProtocol import SerialProtocol

class HeaterBoard:
    def __init__(self, port="COM19"): #TBD take port as input from frontend
        self.serial_model = SerialProtocol(port="COM19", baudrate=115200, timeout=1)

    def setHeaterPowers(self, ch8, ch7, ch6, ch5, ch4, ch3, ch2, ch1):
        command = f"8,{ch8},{ch7},{ch6},{ch5},{ch4},{ch3},{ch2},{ch1}"
        future = self.serial_model.send_command_async(command)  # Use the asynchronous method
        future.add_done_callback(self.handle_response)  # Handle the response when done

    def handle_response(self, future):
        try:
            response = future.result()
            # print(f"Async Response: {response}")
        except Exception as e:
            print(f"Error in async response: {e}")

    def stopHeaters(self):
        command = "8,1,1,1,1,1,1,1,1"
        future = self.serial_model.send_command_async(command)  # Use the asynchronous method
        future.add_done_callback(self.handle_response)  # Handle the response when done
        print("Heater stopped")

    def enableWatchdog(self, event):
        command = f"E"
        future = self.serial_model.send_command_async(command)  # Use the asynchronous method
        future.add_done_callback(self.handle_response)  # Handle the response when done

    def disableWatchdog(self, event):
        command = f"D"
        future = self.serial_model.send_command_async(command)  # Use the asynchronous method
        future.add_done_callback(self.handle_response)  # Handle the response when done

