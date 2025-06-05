#!/usr/bin/env python3
import pandas as pd
import numpy as np
import warnings
warnings.simplefilter("ignore")

from imblearn.over_sampling import SMOTE
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.utils.class_weight import compute_class_weight
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    balanced_accuracy_score,
    matthews_corrcoef,
)
import joblib
import os
import sys

def main():
    # LOAD DATA
    dataset = sys.argv[1]
    df = pd.read_csv(dataset, parse_dates=['timestamp'])
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)

    # FEATURES & LABELS
    FEATURES = [c for c in df.columns if c not in ['timestamp', 'symbol', 'label']] # for demonstration purposes. Not exactly what I use
    X = df[FEATURES]
    y = df['label']

    # BASIC TIME-AWARE 80/20 SPLIT
    split_idx = int(0.8 * len(df))
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    print("Train size:", len(X_train), "Test size:", len(X_test))
    print("Train label dist:\n", y_train.value_counts(normalize=True).sort_index())
    print("Test label dist:\n", y_test.value_counts(normalize=True).sort_index())

    # SMOTE OVERSAMPLING (TRAIN-ONLY) + RANDOM FOREST
    smote = SMOTE(random_state=42)
    X_tr_sm, y_tr_sm = smote.fit_resample(X_train, y_train)
    print("\nAfter SMOTE (train) dist:\n", pd.Series(y_tr_sm).value_counts(normalize=True).sort_index())

    rf_smote = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf_smote.fit(X_tr_sm, y_tr_sm)
    preds_rf_smote = rf_smote.predict(X_test)
    print("\nRF + SMOTE Classification Report:")
    print(classification_report(y_test, preds_rf_smote, digits=4))
    print("RF + SMOTE Confusion Matrix:")
    print(confusion_matrix(y_test, preds_rf_smote))
    print("RF + SMOTE Balanced Acc:", balanced_accuracy_score(y_test, preds_rf_smote))
    print("RF + SMOTE MCC:      ", matthews_corrcoef(y_test, preds_rf_smote))

    # COST-SENSITIVE LEARNING WITH CLASS WEIGHTS
    classes = np.unique(y_train)
    weights = compute_class_weight(class_weight='balanced', classes=classes, y=y_train)
    cw_dict = dict(zip(classes, weights))
    print("\nClass weights:", cw_dict)

    # RandomForest with class_weight
    rf_cw = RandomForestClassifier(
        n_estimators=100,
        class_weight=cw_dict,
        random_state=42,
        n_jobs=-1
    )
    rf_cw.fit(X_train, y_train)
    preds_rf_cw = rf_cw.predict(X_test)
    print("\nRF + Class Weights Classification Report:")
    print(classification_report(y_test, preds_rf_cw, digits=4))
    print("RF + Class Weights Confusion Matrix:")
    print(confusion_matrix(y_test, preds_rf_cw))
    print("RF + Class Weights Balanced Acc:", balanced_accuracy_score(y_test, preds_rf_cw))
    print("RF + Class Weights MCC:      ", matthews_corrcoef(y_test, preds_rf_cw))

    # XGBoost with sample weights
    sample_weights = y_train.map(cw_dict)
    xgb_cw = XGBClassifier(
        objective='multi:softprob',
        num_class=3,
        learning_rate=0.1,
        max_depth=5,
        n_estimators=200,
        eval_metric='mlogloss',
        use_label_encoder=False,
        random_state=42
    )
    xgb_cw.fit(X_train, y_train, sample_weight=sample_weights)
    preds_xgb_cw = xgb_cw.predict(X_test)
    print("\nXGBoost + Class Weights Classification Report:")
    print(classification_report(y_test, preds_xgb_cw, digits=4))
    print("XGBoost + Class Weights Confusion Matrix:")
    print(confusion_matrix(y_test, preds_xgb_cw))
    print("XGBoost + Class Weights Balanced Acc:", balanced_accuracy_score(y_test, preds_xgb_cw))
    print("XGBoost + Class Weights MCC:      ", matthews_corrcoef(y_test, preds_xgb_cw))

    # ROLLING CROSS-VALIDATION (TIMESERIESSPLIT)
    print("\n### Rolling CV w/ TimeSeriesSplit ###")
    n_splits = 5
    tscv = TimeSeriesSplit(n_splits=n_splits)

    rf_smote_scores = []
    rf_cw_scores = []
    xgb_cw_scores = []

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        print(f"\n--- Fold {fold_idx} ---")
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        # SMOTE inside this fold
        sm_f = SMOTE(random_state=42)
        X_tr_sm_f, y_tr_sm_f = sm_f.fit_resample(X_tr, y_tr)

        model_rf_sm = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        model_rf_sm.fit(X_tr_sm_f, y_tr_sm_f)
        pred_rf_sm = model_rf_sm.predict(X_val)
        bal_acc_rf_sm_f = balanced_accuracy_score(y_val, pred_rf_sm)
        rf_smote_scores.append(bal_acc_rf_sm_f)
        print("RF+SMOTE Balanced Acc:", bal_acc_rf_sm_f)

        # Class weights inside this fold
        cw_f = compute_class_weight(class_weight='balanced', classes=np.unique(y_tr), y=y_tr)
        cw_dict_f = dict(zip(np.unique(y_tr), cw_f))

        model_rf_cw = RandomForestClassifier(
            n_estimators=100,
            class_weight=cw_dict_f,
            random_state=42,
            n_jobs=-1
        )
        model_rf_cw.fit(X_tr, y_tr)
        pred_rf_cw = model_rf_cw.predict(X_val)
        bal_acc_rf_cw_f = balanced_accuracy_score(y_val, pred_rf_cw)
        rf_cw_scores.append(bal_acc_rf_cw_f)
        print("RF+ClassWeights Balanced Acc:", bal_acc_rf_cw_f)

        sw_f = y_tr.map(cw_dict_f)
        model_xgb_cw = XGBClassifier(
            objective='multi:softprob',
            num_class=3,
            learning_rate=0.1,
            max_depth=5,
            n_estimators=200,
            eval_metric='mlogloss',
            use_label_encoder=False,
            random_state=42
        )
        model_xgb_cw.fit(X_tr, y_tr, sample_weight=sw_f)
        pred_xgb_cw = model_xgb_cw.predict(X_val)
        bal_acc_xgb_cw_f = balanced_accuracy_score(y_val, pred_xgb_cw)
        xgb_cw_scores.append(bal_acc_xgb_cw_f)
        print("XGB+ClassWeights Balanced Acc:", bal_acc_xgb_cw_f)

    # SUMMARIZE ROLLING CV
    print("\n## Rolling CV Balanced Accuracy Averages ##")
    print(f"RF+SMOTE : {np.mean(rf_smote_scores):.4f} ± {np.std(rf_smote_scores):.4f}")
    print(f"RF+ClassW: {np.mean(rf_cw_scores):.4f} ± {np.std(rf_cw_scores):.4f}")
    print(f"XGB+ClassW: {np.mean(xgb_cw_scores):.4f} ± {np.std(xgb_cw_scores):.4f}")

    # SAVE THE BEST MODEL(S)
    output_dir = "models"
    os.makedirs(output_dir, exist_ok=True)

    # Save RandomForest + SMOTE
    path_rf_smote = os.path.join(output_dir, "rf_smote.joblib")
    joblib.dump(rf_smote, path_rf_smote)

    # Save RandomForest + Class Weights
    path_rf_cw = os.path.join(output_dir, "rf_classweights.joblib")
    joblib.dump(rf_cw, path_rf_cw)

    # Save XGBoost + Class Weights
    path_xgb_cw = os.path.join(output_dir, "xgb_classweights.json")
    xgb_cw.save_model(path_xgb_cw)

    print("\nModels saved to directory:", output_dir)

    # Load models for checks
    # Load RF+SMOTE
    loaded_rf_smote = joblib.load(path_rf_smote)

    # Load RF+ClassWeights
    loaded_rf_cw = joblib.load(path_rf_cw)

    # Load XGB+ClassWeights
    loaded_xgb_cw = XGBClassifier(objective='multi:softprob',
                                  num_class=3,
                                  learning_rate=0.1,
                                  max_depth=5,
                                  n_estimators=200,
                                  eval_metric='mlogloss',
                                  use_label_encoder=False,
                                  random_state=42)
    loaded_xgb_cw.load_model(path_xgb_cw) 

    # SANITY CHECK ON LOADED MODEL
    print("\nSanity Check (RF+SMOTE):", loaded_rf_smote.score(X_test, y_test))
    print("Sanity Check (RF+ClassWeights):", loaded_rf_cw.score(X_test, y_test))
    print("Sanity Check (XGB+ClassWeights):", loaded_xgb_cw.score(X_test, y_test))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('[USAGE]: model_training.py <path/to/train_data>')
    else:
        main()
