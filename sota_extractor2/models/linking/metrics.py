from fastai.text import *
from sklearn.metrics import confusion_matrix
import seaborn as sn
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass
from IPython.display import HTML, display

@dataclass
class CM:
    tp: float
    fn: float
    fp: float
    tn: float

class Metrics:
    def __init__(self, df, experiment_name="unk"):
        # TODO fix this, it mask the fact that our model may return more values than it should for "model
        self.df = df[~df["model_type_gold"].str.contains('not-present') | df["model_type_pred"].str.contains('model-best')]
        self.experiment_name = experiment_name
        self.metric_type = 'best'

    def matching(self, *col_names):
        return np.all([self.df[f"{name}_pred"] == self.df[f"{name}_gold"] for name in col_names], axis=0)

    def matching_fraction(self, *col_names):
        return self.matching(*col_names).sum() / len(self.df)

    def is_predicted_as_relevant(self, *col_names):
        np.all([self.df[f"{name}_pred"]])

    def binary_confusion_matrix(self, *col_names):
        relevant_pred = self.df["model_type_pred"].str.contains('model-best')
        relevant_gold = self.df["model_type_gold"].str.contains('model-best')
        # present_pred  = np.all([self.df[f"{name}_pred"] != 'not-present' for name in col_names], axis=0)

        pred_positive = relevant_pred  # & present_pred
        gold_positive = relevant_gold
        equal = self.matching(*col_names)

        tp = (equal & pred_positive & gold_positive).sum()
        tn = (equal & ~pred_positive & ~gold_positive).sum()
        fp = (pred_positive & (~equal | ~gold_positive)).sum()
        fn = (gold_positive & (~equal | ~pred_positive)).sum()

        return CM(tp=tp, tn=tn, fp=fp, fn=fn)

    def calc_metric(self, metric_name, metric_fn, *col_names):
        result = {f"{metric_name}_{col}": metric_fn(self.binary_confusion_matrix(col)) for col in col_names}
        if len(col_names) > 1:
            cm = self.binary_confusion_matrix(*col_names)
            result[f"{metric_name}_all"] = metric_fn(cm)
            result["best_TP_all"] = cm.tp
            result["best_FP_all"] = cm.fp

            # Hack to present count on which precision is done
            relevant_pred = self.df["model_type_pred"].str.contains('model-best')
            relevant_gold = self.df["model_type_gold"].str.contains('model-best')
            result["best_count"] = (relevant_pred | relevant_gold).sum()

        return result

    def accuracy(self, *col_names):
        result = {f"matching_accuracy_{col}": self.matching_fraction(col) for col in col_names}
        if len(col_names) > 1:
            result['matching_accuracy_all'] = self.matching_fraction(*col_names)
        result["matching_count"] = len(self.df)
        return result

    # True Positive  - m
    # False Positive - cell marked as relevant but with incorrect values

    def confusion_matrix(self, name):
        pred_y = np.array(self.df[f"{name}_pred"])
        true_y = np.array(self.df[f"{name}_gold"])
        labels = list(sorted(set(list(true_y) + list(pred_y))))
        cm = confusion_matrix(true_y, pred_y, labels)
        return cm, labels

    def plot_confusion_matrix(self, name):
        cm, target_names = self.confusion_matrix(name)
        # cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        df_cm = pd.DataFrame(cm, index=[i for i in target_names],
                             columns=[i for i in target_names])
        plt.figure(figsize=(20, 20))
        ax = sn.heatmap(df_cm,
                        annot=True,
                        square=True,
                        fmt="d",
                        cmap="YlGnBu",
                        mask=cm == 0,
                        linecolor="black",
                        linewidths=0.01)
        ax.set_ylabel("True")
        ax.set_xlabel("Predicted")

    def precision(self, *col_names):
        return self.calc_metric("best_precision", lambda cm: cm.tp / (cm.tp + cm.fp), *col_names)

    def recall(self, *col_names):
        return self.calc_metric("best_recall", lambda cm: cm.tp / (cm.tp + cm.fn), *col_names)

    def metrics(self):
        cols = ["dataset", "metric", "task", "format", "parsed"]
        m = self.accuracy(*cols)
        m.update(self.precision(*cols))
        m.update(self.recall(*cols))
        m["experiment_name"] = self.experiment_name
        m["test_type"] = self.metric_type
        return m

    def errors(self, *col_names):
        cols = col_names
        if not cols:
            cols = ["dataset", "metric", "task", "format", "parsed"]
        return self.df[~self.matching(*cols)]

    def show(self, df):
        df = df.copy()
        df['cell_id'] = df.index.map(
            lambda x: '<a target="labeler" href="http://10.0.1.145:8001/paper/{0}">link</a>'.format(x))
        old_width = pd.get_option('display.max_colwidth')
        pd.set_option('display.max_colwidth', -1)
        display(HTML(df.to_html(escape=False)))
        pd.set_option('display.max_colwidth', old_width)

    def show_errors(self):
        self.show(self.errors())