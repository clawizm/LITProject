import LITGuiWithClasses
import LITSubsystemInterface
import ObjectDetectionModel
import multiprocessing
import argparse
from ObjectDetectionModel import ObjectDetectionModel
from LITSubsystemInterface import LITSubsystemData
from LITGuiWithClasses import LITGUI


def run_gui_process(lit_subsystem_data: LITSubsystemData, object_detect_status: bool, model_path: str='', label_path: str='', camera_idx: int = 0, use_tpu: bool = False):
    if object_detect_status:
        from tensorflow.lite.python.interpreter import Interpreter 
        from tensorflow.lite.python.interpreter import load_delegate
        object_detection_model = ObjectDetectionModel(model_path=model_path, use_edge_tpu=use_tpu, camera_index=camera_idx, label_path=label_path)
        lit_subsystem_data.set_object_detection_model(object_detection_model)
        gui = LITGUI(lit_subsystem_data)
        lit_subsystem_data.object_detection_model.set_image_window(f'-CAMERA_{lit_subsystem_data.camera_idx}_FEED-')
        lit_subsystem_data.object_detection_model.set_window(gui.window)
    else:
        gui = LITGUI(lit_subsystem_data)
    gui.start_event_loop()
    return

def start_gui(lit_subsystem_data: LITSubsystemData, object_detect_status: bool, model_path: str='', label_path: str='', camera_idx: int = 0, use_tpu: bool = False):
    p = multiprocessing.Process(target=run_gui_process, args=(lit_subsystem_data,object_detect_status, model_path, label_path, camera_idx, use_tpu))
    p.start()
    return p

def set_command_line_arguments()->argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--performance_mode", help="(Optional) Run subsystems in parallel", action="store_true")
    parser.add_argument("--host", help='(Optional) Local IP address of the server for sending data', action='store')
    # parser.add_argument("--ports", help='(Optional) Local IP address of the server for sending data', action='store')
    # parser.add_argument("--host", help='(Optional) Local IP address of the server for sending data', action='store')

    return parser


if __name__ == '__main__':
    parser = set_command_line_arguments()
    args = parser.parse_args()
    performance_status = args.performance_mode
    model_path = r'C:\Users\brand\Documents\seniordesign\LITProject-NewApproach\ModelFiles\detect.tflite'
    label_path = r'C:\Users\brand\Documents\seniordesign\LITProject-NewApproach\ModelFiles\labelmap.txt'
    wifi_host='192.168.0.220'
    ethernet_host = '192.168.1.2'
    ports = [5000, 5001]
    subsystem_one = LITSubsystemData(0, number_of_leds=256, number_of_sections=8)
    subsystem_two = LITSubsystemData(1,number_of_leds=256, number_of_sections=8)
    subsystem_list = [subsystem_one, subsystem_two]
    if performance_status:
        process1 = start_gui(subsystem_one, False, model_path, label_path, 0, False)
        process2 = start_gui(subsystem_two, False, model_path, label_path, 1, False)
        process1.join()
        process2.join()
    else:
        # object_detection_model_one = ObjectDetectionModel(model_path=model_path, use_edge_tpu=False, camera_index=0, label_path=label_path)
        # object_detection_model_two = ObjectDetectionModel(model_path=model_path, use_edge_tpu=False, camera_index=1, label_path=label_path)
        models = []
        lit_gui = LITGUI(subsystem_list)
        for model, subsystem in zip(models, subsystem_list):
            subsystem.set_object_detection_model(model)
            subsystem.object_detection_model.set_image_window(f'-CAMERA_{model.camera_index}_FEED-')
            subsystem.object_detection_model.set_window(lit_gui.window)
        lit_gui.start_event_loop()
