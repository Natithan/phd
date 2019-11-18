# %% Imports
from __future__ import unicode_literals, print_function

import os
from pathlib import Path

from spacy.lang.en import English  # updated
import matplotlib
import matplotlib.pyplot as plt
from allennlp.data import DatasetReader, Instance, Token, Vocabulary
from allennlp.data.fields import TextField, SequenceLabelField
from allennlp.data.token_indexers import SingleIdTokenIndexer

matplotlib.use('TkAgg')
import torch
import torch.nn as nn
import nltk
from torch.nn.modules.activation import MultiheadAttention
from absl import app
from absl import flags

# %% FLAGS
FLAGS = flags.FLAGS
flags.DEFINE_integer("d_batch", 3, "Batch size")
flags.DEFINE_integer("d_emb", 16, "Embedding size")
flags.DEFINE_integer("nb_heads", 8, "Number of attention heads")
flags.DEFINE_integer("target_length", 20, "Number of tokens in target sequence")
flags.DEFINE_integer("source_length", 20, "Number of tokens in source sequence")
flags.DEFINE_integer("max_seq_length", 20, "Maximum number of words to consider per batch")
flags.DEFINE_string("data_folder", "./data/Gutenberg", "Folder with train, val and test subfolders containing data")

flags.DEFINE_bool("mini", True, "Whether to work with mini data/models for debugging purposes")

# %%

class GutenbergReader(DatasetReader):

    def __init__(self, token_indexers=None):
        super().__init__(lazy=False)
        self.token_indexers = token_indexers or {"tokens": SingleIdTokenIndexer()}

    def text_to_instance(self, tokens, tags=None):
        sentence_field = TextField(tokens, self.token_indexers)
        fields = {"sentence": sentence_field}

        if tags:
            label_field = SequenceLabelField(labels=tags, sequence_field=sentence_field)
            fields["labels"] = label_field

        return Instance(fields)

    def _read(self, folder_path):
        for i, file in enumerate(os.scandir(folder_path)):
            if FLAGS.mini:
                if i > 5:
                    break
            with open(file) as f:
                running_sequence = []
                for line in f:
                    words = line.strip().split()
                    running_sequence += words
                    if len(running_sequence) >= FLAGS.max_seq_length:
                        current_sequence = running_sequence[:FLAGS.max_seq_length]
                        running_sequence = running_sequence[FLAGS.max_seq_length:]
                        yield self.text_to_instance([Token(word) for word in current_sequence])

class FullModel(nn.Module):
    def __init__(self):
        self.attention = AttentionLayer()

    def forward(self, input):
        embedded = self.embedding(input)
        encoded = self.attention(embedded)
        # TODO decide on task: MLM, LM, permutation LM





class AttentionLayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.multihead_attention = MultiHeadAttention()
        self.feedforward = nn.Linear(FLAGS.d_emb, FLAGS.d_emb)

    def forward(self, input):
        att_out = self.multihead_attention(input) + input  # Include skip-connection
        ff_out = self.feedforward(att_out) + att_out
        return ff_out


class MultiHeadAttention(nn.Module):

    def __init__(self):
        super().__init__()
        self.project_q = nn.Linear(FLAGS.d_emb, FLAGS.d_emb)
        self.project_k = nn.Linear(FLAGS.d_emb, FLAGS.d_emb)
        self.project_v = nn.Linear(FLAGS.d_emb, FLAGS.d_emb)

    def forward(self, input):
        q = self.project_q(input)
        k = self.project_k(input)
        v = self.project_v(input)
        assert FLAGS.d_emb % FLAGS.nb_heads == 0
        d_head_emb = FLAGS.d_emb // FLAGS.nb_heads
        q_multi_parts = q.contiguous().view(FLAGS.d_batch * FLAGS.nb_heads, FLAGS.target_length, d_head_emb)
        k_multi_parts = k.contiguous().view(FLAGS.d_batch * FLAGS.nb_heads, FLAGS.source_length, d_head_emb)
        v_multi_parts = v.contiguous().view(FLAGS.d_batch * FLAGS.nb_heads, FLAGS.source_length, d_head_emb)
        att_weights = torch.bmm(q_multi_parts, k_multi_parts.transpose(1, 2))
        att_output_multi_parts = torch.bmm(att_weights, v_multi_parts)
        att_output = att_output_multi_parts.contiguous().view(FLAGS.d_batch, FLAGS.target_length, FLAGS.d_emb)
        return att_output


def main(_):
    reader = GutenbergReader()
    train_dataset = reader.read(os.path.join(FLAGS.data_folder,'train'))
    test_dataset = reader.read(os.path.join(FLAGS.data_folder,'test'))
    val_dataset = reader.read(os.path.join(FLAGS.data_folder,'val'))
    vocab = Vocabulary.from_instances(train_dataset+val_dataset)

    input = torch.rand(FLAGS.d_batch, FLAGS.source_length, FLAGS.d_emb)
    output = AttentionLayer()(input)
    # loss =
    print(output)


if __name__ == '__main__':
    app.run(main)
