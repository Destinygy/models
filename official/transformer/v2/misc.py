# Copyright 2019 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Misc for Transformer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import flags

from official.transformer.model import model_params
from official.utils.flags import core as flags_core

PARAMS_MAP = {
    "tiny": model_params.TINY_PARAMS,
    "base": model_params.BASE_PARAMS,
    "big": model_params.BIG_PARAMS,
}


def get_model_params(param_set, num_gpus):
  """Gets predefined model params."""
  if num_gpus > 1:
    if param_set == "big":
      return model_params.BIG_MULTI_GPU_PARAMS.copy()
    elif param_set == "base":
      return model_params.BASE_MULTI_GPU_PARAMS.copy()
    else:
      raise ValueError("Not valid params: param_set={} num_gpus={}".format(
          param_set, num_gpus))

  return PARAMS_MAP[param_set].copy()


def define_transformer_flags():
  """Add flags and flag validators for running transformer_main."""
  # Add common flags (data_dir, model_dir, train_epochs, etc.).
  flags_core.define_base()
  flags_core.define_performance(
      num_parallel_calls=True,
      inter_op=False,
      intra_op=False,
      synthetic_data=True,
      max_train_steps=False,
      dtype=False,
      all_reduce_alg=True
  )
  flags_core.define_benchmark()
  flags_core.define_device(tpu=True)

  # Set flags from the flags_core module as "key flags" so they're listed when
  # the '-h' flag is used. Without this line, the flags defined above are
  # only shown in the full `--helpful` help text.
  flags.adopt_module_key_flags(flags_core)

  # Add transformer-specific flags
  flags.DEFINE_enum(
      name="param_set", short_name="mp", default="big",
      enum_values=PARAMS_MAP.keys(),
      help=flags_core.help_wrap(
          "Parameter set to use when creating and training the model. The "
          "parameters define the input shape (batch size and max length), "
          "model configuration (size of embedding, # of hidden layers, etc.), "
          "and various other settings. The big parameter set increases the "
          "default batch size, embedding/hidden size, and filter size. For a "
          "complete list of parameters, please see model/model_params.py."))

  flags.DEFINE_bool(
      name="static_batch", default=False,
      help=flags_core.help_wrap(
          "Whether the batches in the dataset should have static shapes. In "
          "general, this setting should be False. Dynamic shapes allow the "
          "inputs to be grouped so that the number of padding tokens is "
          "minimized, and helps model training. In cases where the input shape "
          "must be static (e.g. running on TPU), this setting will be ignored "
          "and static batching will always be used."))

  # Flags for training with steps (may be used for debugging)
  flags.DEFINE_integer(
      name="steps_per_epoch", short_name="sbe", default=1000,
      help=flags_core.help_wrap(
          "The number of training steps for each epoch."))
  flags.DEFINE_integer(
      name="init_epoch", short_name="is", default=0,
      help=flags_core.help_wrap("The number of initial epoch for training."))
  flags.DEFINE_string(
      name="init_weight_path", short_name="iwp", default=None,
      help=flags_core.help_wrap("The initial model weights to load."))
  flags.DEFINE_string(
      name="init_logdir_timestamp", short_name="ilt", default=None,
      help=flags_core.help_wrap("The initial timestamp for logdir."))
  flags.DEFINE_integer(
      name="validation_steps", short_name="vs", default=64,
      help=flags_core.help_wrap("The number of steps used in validation."))

  # BLEU score computation
  flags.DEFINE_string(
      name="bleu_source", short_name="bls", default=None,
      help=flags_core.help_wrap(
          "Path to source file containing text translate when calculating the "
          "official BLEU score. Both --bleu_source and --bleu_ref must be set. "
          "Use the flag --stop_threshold to stop the script based on the "
          "uncased BLEU score."))
  flags.DEFINE_string(
      name="bleu_ref", short_name="blr", default=None,
      help=flags_core.help_wrap(
          "Path to source file containing text translate when calculating the "
          "official BLEU score. Both --bleu_source and --bleu_ref must be set. "
          "Use the flag --stop_threshold to stop the script based on the "
          "uncased BLEU score."))
  flags.DEFINE_string(
      name="vocab_file", short_name="vf", default=None,
      help=flags_core.help_wrap(
          "Path to subtoken vocabulary file. If data_download.py was used to "
          "download and encode the training data, look in the data_dir to find "
          "the vocab file."))
  flags.DEFINE_string(
      name="mode", default="train",
      help=flags_core.help_wrap("mode: train, eval, or predict"))

  flags_core.set_defaults(data_dir="/tmp/translate_ende",
                          model_dir="/tmp/transformer_model",
                          batch_size=None,
                          train_epochs=10)

  # pylint: disable=unused-variable
  @flags.multi_flags_validator(
      ["mode", "train_epochs"],
      message="--train_epochs must be defined in train mode")
  def _check_train_limits(flag_dict):
    if flag_dict["mode"] == "train":
      return flag_dict["train_epochs"] is not None
    return True

  @flags.multi_flags_validator(
      ["bleu_source", "bleu_ref"],
      message="Both or neither --bleu_source and --bleu_ref must be defined.")
  def _check_bleu_files(flags_dict):
    return (flags_dict["bleu_source"] is None) == (
        flags_dict["bleu_ref"] is None)

  @flags.multi_flags_validator(
      ["bleu_source", "bleu_ref", "vocab_file"],
      message="--vocab_file must be defined if --bleu_source and --bleu_ref "
              "are defined.")
  def _check_bleu_vocab_file(flags_dict):
    if flags_dict["bleu_source"] and flags_dict["bleu_ref"]:
      return flags_dict["vocab_file"] is not None
    return True

  @flags.multi_flags_validator(
      ["export_dir", "vocab_file"],
      message="--vocab_file must be defined if --export_dir is set.")
  def _check_export_vocab_file(flags_dict):
    if flags_dict["export_dir"]:
      return flags_dict["vocab_file"] is not None
    return True
  # pylint: enable=unused-variable

  flags_core.require_cloud_storage(["data_dir", "model_dir", "export_dir"])
