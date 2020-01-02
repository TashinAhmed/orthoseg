# -*- coding: utf-8 -*-
"""
Module with helper functions regarding (keras) models.
"""

import logging
from pathlib import Path
import shutil
from typing import Optional

import pandas as pd 
from tensorflow import keras as kr

#-------------------------------------------------------------
# First define/init some general variables/constants
#-------------------------------------------------------------
# Get a logger...
logger = logging.getLogger(__name__)
#logger.setLevel(logging.INFO)

#-------------------------------------------------------------
# The real work
#-------------------------------------------------------------

def get_max_data_version(model_dir: Path) -> int:
    """
    Get the maximum data version a model exists for in the model_dir.
    
    Args
        model_dir: the dir to search models in
    """
    models_df = get_models(model_dir)
    if models_df is not None and len(models_df.index) > 0:
        traindata_version_max = models_df['traindata_version'].max()
        return int(traindata_version_max)
    else:
        return -1

def format_model_basefilename(
        segment_subject: str,
        traindata_version: int,
        model_architecture: str,
        hyperparams_version: int) -> str:
    """
    Format the parameters into a model_filename.
    
    Args
        segment_subject: the segment subject
        traindata_version: the version of the data used to train the model
        model_architecture: the architecture of the model
        hyperparams_version: the version of the hyper parameters used to train
    """
    # Format file name
    filename = f"{segment_subject}_{traindata_version:02d}_{model_architecture}"
    if hyperparams_version > 0:
        filename += f"+{hyperparams_version:02d}"
    return filename

def format_model_filename(
        segment_subject: str,
        traindata_version: int,
        model_architecture: str,
        hyperparams_version: int,
        acc_train: float,
        acc_val: float,
        acc_combined: float,
        epoch: int,
        save_format: str) -> str:
    """
    Format the parameters into a model_filename.
    
    Args
        segment_subject: the segment subject
        traindata_version: the version of the data used to train the model
        model_architecture: the architecture of the model
        hyperparams_version: the version of the hyper parameters used to train
        acc_train: the accuracy reached for the training dataset
        acc_val: the accuracy reached for the validation dataset
        acc_combined: the average of the train and validation accuracy
        epoch: the epoch during training that reached these model weights
        save_format (str): the format to save in: 'h5' (keras format) or 'tf' (tensorflow savedmodel)
    """
    # Format file name
    filename = format_model_basefilename(
            segment_subject=segment_subject,
            traindata_version=traindata_version,
            model_architecture=model_architecture,
            hyperparams_version=hyperparams_version)
    filename += f"_{acc_combined:.5f}_{acc_train:.5f}_{acc_val:.5f}_{epoch}"

    # Add suffix
    if save_format == 'tf':
        filename += "_tf"
    else:
        filename += ".hdf5"

    return filename

def parse_model_filename(filepath: Path) -> Optional[dict]:
    """
    Parse a model_filename to a dict containing the properties of the model:
        * segment_subject: the segment subject
        * traindata_version: the version of the data used to train the model
        * model_architecture: the architecture of the model
        * hyperparams_version: the version of the hyper parameters used to train
        * acc_train: the accuracy reached for the training dataset
        * acc_val: the accuracy reached for the validation dataset
        * acc_combined: the average of the train and validation accuracy
        * epoch: the epoch during training that reached these model weights
        * save_format: the save type of the model: 'h5' or 'tf'  
    
    Args
        filepath: the filepath to the model file
    """
    
    # Prepare filepath to extract info
    if filepath.is_dir():
        # If it is a dir, it should end on _tf
        if not filepath.name.endswith("_tf"):
            logger.warning(f"Not a valid path for a model, dir needs to end on _tf: {filepath}")
            return None
        save_format = 'tf'
        filename = filepath.name
    else:
        filename = filepath.stem
        if filepath.suffix in ('.h5', '.hdf5'):
            save_format = 'h5'
        else: 
            logger.warning(f"Not a valid path for a model, file should have .h5 of .hdf5 as suffix: {filepath}")
            return None
        
    # Now extract the basic fields...
    param_values = filename.split("_")
    if len(param_values) < 3:
        logger.warning(f"Not a valid path for a model, split('_') should result in >= 3 fields: {filepath}")
    segment_subject = param_values[0]
    traindata_version = int(param_values[1])
    model_train_info = param_values[2]

    # If available, extract the hyperparams version, otherwise it is 0
    model_train_info_values = model_train_info.split("+")
    if model_train_info_values[-1].isdigit():
        hyperparams_version = int(model_train_info_values[-1])
        model_architecture = '+'.join(model_train_info_values[:-1])
    else:
        hyperparams_version = 0
        model_architecture = model_train_info

    # If available, extract the acuuracies.
    if(len(param_values) > 3):
        acc_combined = float(param_values[3])
        acc_train = float(param_values[4])
        acc_val = float(param_values[5])
        epoch = int(param_values[6])
    else:
        logger.warning(f"No model accuracy information found in: {filepath}")
        acc_combined = 0.0
        acc_train = 0.0
        acc_val = 0.0
        epoch = 0
    
    basefilename = format_model_basefilename(
            segment_subject=segment_subject,
            traindata_version=traindata_version,
            model_architecture=model_architecture,
            hyperparams_version=hyperparams_version)

    return {'filepath': filepath,
            'filename': filename,
            'basefilename': basefilename,
            'segment_subject': segment_subject,
            'traindata_version': traindata_version,
            'model_architecture': model_architecture,
            'hyperparams_version': hyperparams_version,
            'acc_combined': acc_combined,
            'acc_train': acc_train,
            'acc_val': acc_val,
            'epoch': epoch,
            'save_format': save_format}

def get_models(
        model_dir: Path,
        segment_subject: str = None,
        model_architecture: str = None,
        traindata_version: int = None,
        hyperparams_version: int = None) -> pd.DataFrame:
    """
    Return the list of models in the model_dir passed. It is returned as a 
    dataframe with the columns as returned in parse_model_filename()
    
    Args
        model_dir: dir containing the models
        model_base_filename: optional, if passed, only the models with this 
            base filename will be returned
    """

    # List models
    model_paths = []
    model_paths.extend(model_dir.glob('*.hdf5'))
    model_paths.extend(model_dir.glob('*.h5'))
    model_paths.extend(model_dir.glob('*_tf'))

    # Loop through all models and extract necessary info...
    model_info_list = []
    for model_path in model_paths:
        model_info = parse_model_filename(model_path)
        if model_info is not None:
            model_info_list.append(model_info)
    model_info_df = pd.DataFrame(model_info_list)

    # Filter, if filters provided
    if len(model_info_df) > 0:
        if segment_subject is not None:
            model_info_df = model_info_df.loc[model_info_df['segment_subject'] == segment_subject]
        if model_architecture is not None:
            model_info_df = model_info_df.loc[model_info_df['model_architecture'] == model_architecture]
        if traindata_version is not None:
            model_info_df = model_info_df.loc[model_info_df['traindata_version'] == traindata_version]
        if hyperparams_version is not None:
            model_info_df = model_info_df.loc[model_info_df['hyperparams_version'] == hyperparams_version]

    return model_info_df

def get_best_model(
        model_dir: Path,
        segment_subject: str = None,
        traindata_version: int = None,
        model_architecture: str = None,
        hyperparams_version: int = None) -> Optional[dict]:
    """
    Get the properties of the model with the highest combined accuracy for the highest 
    traindata version in the dir.

    Remark: regardless of the monitor function used when training, the accuracies
    are always better if higher!
    
    Args
        model_dir: dir containing the models
        segment_subject (str, optional): only models with this the segment subject 
        traindata_version (str, optional): only models with this train data version
        model_architecture (str, optional): only models with this model architecture
        hyperparams_version (str, optional): only models with this trainparams version
        
    Returns
        A dictionary with the info of the best model, or None if no model was found
    """
    # Get list of existing models for this train dataset
    model_info_df = get_models(
            model_dir=model_dir,
            segment_subject=segment_subject,
            model_architecture=model_architecture,
            traindata_version=traindata_version,
            hyperparams_version=hyperparams_version)
    
    # If no traindata_version provided, take highest data version
    if traindata_version is None:
        max_data_version = get_max_data_version(model_dir)
        if max_data_version == -1:
            return None
        model_info_df = model_info_df.loc[model_info_df['traindata_version'] == max_data_version]
    
    if len(model_info_df) > 0:
        model_info_df = model_info_df.reset_index()     
        return model_info_df.loc[model_info_df['acc_combined'].values.argmax()]
    else:
        return None
    
class ModelCheckpointExt(kr.callbacks.Callback):
    
    def __init__(
            self, 
            model_save_dir: Path,
            segment_subject: str,
            traindata_version: int,
            model_architecture: str,
            hyperparams_version: int,
            monitor_metric_mode: str,
            monitor_metric_train: str,
            monitor_metric_validation: str,
            save_format: str = 'tf',
            save_best_only: bool = False,
            save_weights_only: bool = False,
            model_template_for_save = None,
            verbose: bool = True,
            only_report: bool = False):
        """
        Constructor
        
        Args:
            model_save_dir (Path): [description]
            segment_subject (str): segment subject 
            traindata_version (int): train data version
            model_architecture (str): model architecture
            hyperparams_version (int): version of the hyper parameters used
            monitor_metric_mode (str): use 'min' if the accuracy metrics should be 
                    as low as possible, 'max' if a higher values is better. 
            monitor_metric_train (str): The metric to monitor for train accuracy
            monitor_metric_validation (str): The metric to monitor for validation accuracy
            save_format (str, optional): The format to save in: 'h5' (keras format) or 'tf' (tensorflow savedmodel). Defaults to 'tf'
            save_best_only: optional: only keep the best model
            save_weights_only: optional: only save weights
            model_template_for_save: optional, if using multi-GPU training, pass
                the original model here to use this as template for saving        
            verbose (bool, optional): [description]. Defaults to True.
            only_report (bool, optional): [description]. Defaults to False.
        """
        monitor_metric_mode_values = ['min', 'max']
        if(monitor_metric_mode not in monitor_metric_mode_values):
            raise Exception(f"Invalid value for mode: {monitor_metric_mode}, should be one of {monitor_metric_mode_values}")
        save_format_values = ('h5', 'tf')
        if save_format not in save_format_values:
            raise Exception(f"Invalid value for save_format: {save_format}, should be one of {save_format_values}")
        
        self.model_save_dir = model_save_dir
        self.segment_subject = segment_subject
        self.traindata_version = traindata_version
        self.model_architecture = model_architecture
        self.hyperparams_version = hyperparams_version
        self.monitor_metric_train = monitor_metric_train
        self.monitor_metric_validation = monitor_metric_validation
        self.monitor_metric_mode = monitor_metric_mode
        self.save_format = save_format
        self.save_best_only = save_best_only
        self.save_weights_only = save_weights_only
        self.model_template_for_save = model_template_for_save
        self.verbose = verbose
        self.only_report = only_report
        
    def on_epoch_end(self, epoch, logs={}):
        logger.debug("Start in callback on_epoch_begin")
        
        save_and_clean_models(
                model_save_dir=self.model_save_dir,
                segment_subject=self.segment_subject,
                traindata_version=self.traindata_version,
                model_architecture=self.model_architecture,
                hyperparams_version=self.hyperparams_version,
                monitor_metric_mode=self.monitor_metric_mode,
                new_model=self.model,
                new_model_monitor_train=logs.get(self.monitor_metric_train),
                new_model_monitor_val=logs.get(self.monitor_metric_validation),
                new_model_epoch=epoch,
                save_format=self.save_format,
                save_best_only=self.save_best_only,          
                save_weights_only=self.save_weights_only,
                model_template_for_save=self.model_template_for_save,      
                verbose=self.verbose,
                only_report=self.only_report)
        
def save_and_clean_models(
        model_save_dir: Path,
        segment_subject: str,
        traindata_version: int,        
        model_architecture: str,
        hyperparams_version: int,
        monitor_metric_mode: str,
        new_model = None,        
        new_model_monitor_train: Optional[float] = None,
        new_model_monitor_val: Optional[float] = None,
        new_model_epoch: Optional[int] = None,
        save_format: str = 'tf',
        save_best_only: bool = False,
        save_weights_only: bool = False,
        model_template_for_save = None, 
        verbose: bool = True,
        debug: bool = False,
        only_report: bool = False):
    """
    Save the new model if it is good enough... and cleanup existing models 
    if they are worse than the new or other existing models.
    
    Args
        model_save_dir (Path): dir containing the models
        segment_subject (str): segment subject 
        traindata_version (int): train data version
        model_architecture (str): model architecture
        hyperparams_version (int): version of the train params
        model_monitor_metric_mode (str): use 'min' if the monitored metrics should be 
                as low as possible, 'max' if a higher values is better. 
        new_model (optional): the keras model object that will be saved
        new_model_monitor_train (float, optional): the monitored metric on the train dataset
        new_model_monitor_val (float, optional): the monitored metric on the validation dataset
        new_model_epoch (int, optional): the epoch in the training
        save_format (str, optional): The format to save in: 'h5' (keras format) or 'tf' (tensorflow savedmodel). Defaults to 'tf'
        save_best_only (bool, optional): only keep the best model
        save_weights_only (bool, optional): only save weights
        model_template_for_save (optional): if using multi-GPU training, pass
            the original model here to use this as template for saving        
        verbose (bool, optional): report the best model after save and cleanup
        debug (bool, optional): write debug logging
        only_report (bool, optional): only report which models would be cleaned up
    """
    # TODO: add option to specify minimum accuracy/iou score before saving to speed up, because saving takes quite some time! 
    # Check validaty of input
    monitor_metric_mode_values = ['min', 'max']
    if(monitor_metric_mode not in monitor_metric_mode_values):
        raise Exception(f"Invalid value for mode: {monitor_metric_mode}, should be one of {monitor_metric_mode_values}")
    save_format_values = ('h5', 'tf')
    if save_format not in save_format_values:
        raise Exception(f"Invalid value for save_format: {save_format}, should be one of {save_format_values}")
            
    # Get a list of all existing models
    model_info_df = get_models(
            model_dir=model_save_dir, 
            segment_subject=segment_subject,
            model_architecture=model_architecture,
            traindata_version=traindata_version,
            hyperparams_version=hyperparams_version)

    # If there is a new model passed as param, add it to the list
    new_model_path = None
    if new_model is not None:
        
        if(new_model_monitor_train is None
           or new_model_monitor_val is None
           or new_model_epoch is None):
            raise Exception(f"If new_model is not None, new_model_monitor_... parameters cannot be None either???, new_model_monitor_train: {new_model_monitor_train}, new_model_monitor_val: {new_model_monitor_val}, new_model_epoch: {new_model_epoch}")
                    
        # Calculate combined accuracy
        new_model_monitor_combined = (new_model_monitor_train+new_model_monitor_val)/2
        
        # Build save filepath
        # Remark: accuracy values should always be as high as possible, so 
        # recalculate values if monitor_metric_mode is 'min'
        if monitor_metric_mode == 'max':
            new_model_acc_combined = new_model_monitor_combined
            new_model_acc_train = new_model_monitor_train
            new_model_acc_val = new_model_monitor_val
        else:
            new_model_acc_combined = 1-new_model_monitor_combined
            new_model_acc_train = 1-new_model_monitor_train
            new_model_acc_val = 1-new_model_monitor_val
        
        new_model_filename = format_model_filename(
                segment_subject=segment_subject,
                traindata_version=traindata_version,
                model_architecture=model_architecture,
                hyperparams_version=hyperparams_version,
                acc_combined=new_model_acc_combined,
                acc_train=new_model_acc_train, 
                acc_val=new_model_acc_val, 
                epoch=new_model_epoch,
                save_format=save_format)
        new_model_path = Path(model_save_dir) / new_model_filename
        
        # Append model to the retrieved models...
        model_info_df = model_info_df.append({  'filepath': str(new_model_path),
                                                'filename': new_model_filename,
                                                'segment_subject': segment_subject,
                                                'traindata_version': traindata_version,
                                                'model_architecture': model_architecture,
                                                'hyperparams_version': hyperparams_version,
                                                'acc_combined': new_model_acc_combined,
                                                'acc_train': new_model_acc_train,
                                                'acc_val': new_model_acc_val,
                                                'epoch': new_model_epoch,
                                                'save_format': save_format 
                                             },
                                             ignore_index=True)

    # Loop through all existing models
    # Remark: the list is sorted descending before iterating it, this way new
    # models are saved bevore deleting the previous best one(s)
    model_info_sorted_df = model_info_df.sort_values(by='acc_combined', ascending=False)
    for _, model_info in model_info_sorted_df.iterrows():
       
        # If only the best needs to be kept, check only on acc_combined...
        keep_model = True
        if save_best_only:
            better_ones_df = model_info_df[
                    (model_info_df['filepath'] != model_info['filepath']) 
                     & (model_info_df['acc_combined'] >= model_info['acc_combined'])]
            if len(better_ones_df) > 0:
                keep_model = False
        else:
            # If not only best to be kept, check if there is a model with ALL 
            # parameters higher than itself, if so: no use in keeping it.
            better_ones_df = model_info_df[
                    (model_info_df['filepath'] != model_info['filepath']) 
                     & (model_info_df['acc_combined'] >= model_info['acc_combined']) 
                     & (model_info_df['acc_train'] >= model_info['acc_train'])
                     & (model_info_df['acc_val'] >= model_info['acc_val'])]
            if len(better_ones_df) > 0:
                keep_model = False

        # If model is (relatively) ok, keep it
        if keep_model is True:
            logger.debug(f"KEEP {model_info['filename']}")

            # If it is the new model that needs to be kept, keep it or save to disk
            if(new_model_path is not None 
               and only_report is not True
               and model_info['filepath'] == str(new_model_path)
               and not new_model_path.exists()):
                logger.debug('Save model start')
                if save_weights_only:
                    if model_template_for_save is not None:
                        model_template_for_save.save_weights(str(new_model_path))
                    else:                    
                        new_model.save_weights(str(new_model_path))
                else:
                    if model_template_for_save is not None:
                        model_template_for_save.save(str(new_model_path))
                    else:                    
                        new_model.save(str(new_model_path))
                logger.debug('Save model ready')
        else:     
            # Bad model... can be removed (or not saved)
            if only_report is True:
                logger.debug(f"DELETE {model_info['filename']}")
            elif Path(model_info['filepath']).exists() is True:
                logger.debug(f"DELETE {model_info['filename']}")
                if Path(model_info['filepath']).is_dir() is True:
                    shutil.rmtree(model_info['filepath'])
                else:
                    Path(model_info['filepath']).unlink()
                
            if debug is True:
                print(f"Better one(s) found for{model_info['filename']}:")
                for _, better_one in better_ones_df.iterrows():
                    print(f"  {better_one['filename']}")

    if verbose is True or debug is True:
        best_model = get_best_model(
                model_dir=model_save_dir,
                segment_subject=segment_subject,
                model_architecture=model_architecture,
                traindata_version=traindata_version)
        if best_model is not None:
            print(f"\nBEST MODEL: acc_combined: {best_model['acc_combined']}, acc_train: {best_model['acc_train']}, acc_val: {best_model['acc_val']}, epoch: {best_model['epoch']}")

if __name__ == '__main__':
    raise Exception("Not implemented")
