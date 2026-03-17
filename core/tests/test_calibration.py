"""Tests for Phase 2 Confidence Calibration."""

from framework.graph.calibration import CalibrationRecord, calibrate_thresholds


def test_calibrate_thresholds_empty():
    """Test calibration with empty records returns defaults."""
    metrics = calibrate_thresholds([], target_accuracy=0.95)
    assert metrics.recommended_threshold == 0.8
    assert metrics.retry_success_rate == 0.0
    assert not metrics.accept_accuracy_by_confidence
    assert not metrics.threshold_by_goal_type


def test_calibrate_thresholds_perfect_accuracy():
    """Test calibration where LLM and human always agree."""
    records = [
        CalibrationRecord("r1", "s1", "ACCEPT", 0.9, "ACCEPT"),
        CalibrationRecord("r2", "s2", "ACCEPT", 0.8, "ACCEPT"),
        CalibrationRecord("r3", "s3", "RETRY", 0.5, "RETRY"),
    ]
    metrics = calibrate_thresholds(records, target_accuracy=0.9)
    # The lowest confidence that meets the target (100% > 90%) is 0.5, but for ACCEPT records,
    # the threshold calculations include all records, but minimum is 0.5.
    assert metrics.recommended_threshold == 0.5
    assert metrics.retry_success_rate == 1.0
    assert metrics.accept_accuracy_by_confidence[0.9] == 1.0
    assert metrics.accept_accuracy_by_confidence[0.8] == 1.0


def test_calibrate_thresholds_mixed_accuracy():
    """Test calibration where higher confidence yields higher accuracy."""
    records = [
        # At 0.9: 1/1 correct (100%)
        CalibrationRecord("r1", "s1", "ACCEPT", 0.9, "ACCEPT"),
        # At 0.8: 2/3 correct (66%)
        CalibrationRecord("r2", "s2", "ACCEPT", 0.8, "ACCEPT"),
        CalibrationRecord("r3", "s3", "ACCEPT", 0.8, "ACCEPT"),
        CalibrationRecord("r4", "s4", "ACCEPT", 0.8, "RETRY"),  # LLM wrong
        # At 0.7: 1/2 correct (50%)
        CalibrationRecord("r5", "s5", "ACCEPT", 0.7, "ACCEPT"),
        CalibrationRecord("r6", "s6", "ACCEPT", 0.7, "RETRY"),  # LLM wrong
    ]

    # Target 90% accuracy
    # Above 0.7: 4/6 correct (66.6%)
    # Above 0.8: 3/4 correct (75%)
    # Above 0.9: 1/1 correct (100%) -> Meets 90% target!

    metrics = calibrate_thresholds(records, target_accuracy=0.9)
    assert metrics.recommended_threshold == 0.9

    # Target 70% accuracy
    # Above 0.8 is 75%, which meets 70% target
    metrics_70 = calibrate_thresholds(records, target_accuracy=0.7)
    assert metrics_70.recommended_threshold == 0.8


def test_calibrate_thresholds_by_goal_type():
    """Test that thresholds can vary by goal type."""
    records = [
        # security goal needs 0.9 for 100%
        CalibrationRecord("r1", "s1", "ACCEPT", 0.9, "ACCEPT", "security"),
        CalibrationRecord("r2", "s2", "ACCEPT", 0.8, "RETRY", "security"),
        # ux goal achieves 100% even at 0.7
        CalibrationRecord("r3", "s3", "ACCEPT", 0.7, "ACCEPT", "ux"),
        CalibrationRecord("r4", "s4", "ACCEPT", 0.8, "ACCEPT", "ux"),
    ]

    metrics = calibrate_thresholds(records, target_accuracy=0.95)

    assert metrics.threshold_by_goal_type["security"] == 0.9
    assert metrics.threshold_by_goal_type["ux"] == 0.7
