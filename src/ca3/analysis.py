"""Analysis helpers shared by the CA3 Streamlit pages.

The executed notebook keeps its own copy of these functions in
``notebooks/CA3/Proj-P3.py``. This module is the app-side version so the pages
can import tested code without changing the hand-in notebook.

CRS: none. Every function takes a ``pandas.Series`` indexed by time and returns
a figure or a table; no coordinates enter or leave. The spatial work (and the
EPSG:25833 / 4326 / 3035 decisions behind it) lives in the precompute script and
in the CA3 notebook — see ``docs/crs.md``.
"""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from scipy.fft import dct, idct
from scipy.signal import spectrogram
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.seasonal import STL


def _as_series(series: pd.Series) -> pd.Series:
    """Return a float series with a DatetimeIndex and no gaps."""
    values = pd.Series(series).astype(float).interpolate()
    if not isinstance(values.index, pd.DatetimeIndex):
        raise TypeError("series must have a DatetimeIndex")
    if values.empty:
        raise ValueError("series is empty")
    return values


def robust_sigma(values: np.ndarray) -> float:
    """MAD-based standard deviation (1.4826 * median absolute deviation)."""
    centre = np.median(values)
    return float(1.4826 * np.median(np.abs(values - centre)))


def stl_analysis(
    series: pd.Series,
    period: int = 52,
    seasonal: int = 13,
    trend: int = 101,
    robust: bool = True,
) -> tuple[Figure, Any]:
    """STL decomposition of a weekly series; returns the figure and result."""
    values = _as_series(series)
    if len(values) < 2 * period:
        raise ValueError(
            f"Need at least {2 * period} observations for STL, got {len(values)}"
        )
    if seasonal % 2 == 0:
        raise ValueError("seasonal must be an odd integer")
    if trend % 2 == 0 or trend <= period:
        raise ValueError("trend must be odd and larger than period")

    result = STL(
        values.to_numpy(),
        period=period,
        seasonal=seasonal,
        trend=trend,
        robust=robust,
    ).fit()

    fig, axes = plt.subplots(4, 1, figsize=(14, 9), sharex=True)
    panels = (
        ("Observed", values.to_numpy()),
        ("Trend", result.trend),
        ("Seasonal", result.seasonal),
        ("Residual", result.resid),
    )
    for ax, (title, panel_values) in zip(axes, panels):
        ax.plot(values.index, panel_values, linewidth=1.0)
        ax.set_ylabel(title)
        ax.grid(True, alpha=0.3)

    axes[0].set_title(
        f"STL decomposition of {values.name} "
        f"(period={period}, seasonal={seasonal}, trend={trend}, robust={robust})"
    )
    fig.tight_layout()
    return fig, result


def spectrogram_analysis(
    series: pd.Series,
    window: int = 52,
    overlap: int = 26,
    max_frequency: float | None = 0.1,
) -> tuple[Figure, np.ndarray, np.ndarray, np.ndarray]:
    """Spectrogram of a weekly series; frequency is cycles per week."""
    values = _as_series(series)
    if window <= 0 or window > len(values):
        raise ValueError("window must be positive and at most the series length")
    if not 0 <= overlap < window:
        raise ValueError("overlap must be in [0, window)")

    index = values.index
    assert isinstance(index, pd.DatetimeIndex)

    frequencies, times, power = spectrogram(
        values.to_numpy(dtype=float),
        fs=1.0,
        nperseg=window,
        noverlap=overlap,
        detrend="linear",
    )

    # scipy reports segment positions in samples; map them to dates so the
    # horizontal axis is readable.
    step = values.index.to_series().diff().median()
    x = values.index[0] + pd.to_timedelta(times * step.total_seconds(), unit="s")

    fig, ax = plt.subplots(figsize=(14, 5))
    mesh = ax.pcolormesh(
        x,
        frequencies,
        10 * np.log10(power + np.finfo(float).eps),
        shading="auto",
    )
    fig.colorbar(mesh, ax=ax, label="Power [dB]")
    if max_frequency is not None:
        ax.set_ylim(0, min(max_frequency, 0.5))
    ax.set_title(
        f"Spectrogram of {values.name} "
        f"(window={window} weeks, overlap={overlap} weeks)"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Frequency [cycles/week]")
    fig.tight_layout()
    return fig, frequencies, times, power


def spc_outliers(
    series: pd.Series,
    cutoff_per_year: float = 12.0,
    n_std: float = 3.0,
    label: str = "Temperature",
    unit: str = "°C",
) -> tuple[Figure, dict[str, float | int], pd.DataFrame]:
    """SPC outliers from a DCT high-pass (SATV) with robust limits.

    ``cutoff_per_year`` removes variations slower than that many cycles per
    year (12 ≈ one month). The limits follow the slow seasonal baseline:
    ``baseline + median(SATV) ± n_std * robust_sigma(SATV)``. The SATV itself
    is used only for the limits and the outlier flags, never plotted.
    """
    values = _as_series(series)
    if len(values) < 4:
        raise ValueError("Need at least four observations")

    index = values.index
    assert isinstance(index, pd.DatetimeIndex)
    years = (index[-1] - index[0]).total_seconds() / (365.25 * 24 * 3600)
    # DCT coefficient k represents k/2 cycles over the whole series.
    k = int(round(2 * cutoff_per_year * max(years, 1e-6)))
    k = max(1, min(k, len(values) - 1))

    coefficients = np.asarray(
        dct(values.to_numpy(dtype=float), norm="ortho"), dtype=float
    )
    low = coefficients.copy()
    low[k:] = 0  # keep only the slow (seasonal) part
    baseline = idct(low, norm="ortho")
    satv = values.to_numpy(dtype=float) - baseline

    centre = float(np.median(satv))
    sigma = robust_sigma(satv)
    upper = baseline + centre + n_std * sigma
    lower = baseline + centre - n_std * sigma
    is_outlier = np.abs(satv - centre) > n_std * sigma

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(values.index, values, linewidth=0.6, label=f"{label} (area mean)")
    ax.plot(
        values.index,
        upper,
        color="black",
        linewidth=1.0,
        label=f"SPC limits (±{n_std:g} robust σ)",
    )
    ax.plot(values.index, lower, color="black", linewidth=1.0)
    if is_outlier.any():
        ax.scatter(
            values.index[is_outlier],
            values.to_numpy()[is_outlier],
            color="#B35A12",
            s=14,
            zorder=3,
            label=f"Outliers ({int(is_outlier.sum())})",
        )
    ax.set_title(
        f"{label}: {int(is_outlier.sum())} outliers in {len(values):,} hours "
        f"(DCT cut-off {cutoff_per_year:g} cycles/year, {n_std:g}σ)"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel(f"{label} [{unit}]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()

    table = pd.DataFrame(
        {
            "value": values.to_numpy(dtype=float),
            "satv": satv,
            "lower": lower,
            "upper": upper,
        },
        index=values.index,
    )
    table = table.loc[is_outlier]
    table.index.name = "timestamp"

    summary: dict[str, float | int] = {
        "hours": int(len(values)),
        "outliers": int(is_outlier.sum()),
        "share": float(is_outlier.mean()),
        "robust_sigma": sigma,
        "dct_coefficients_removed": k,
        "cutoff_per_year": float(cutoff_per_year),
        "n_std": float(n_std),
    }
    return fig, summary, table


def lof_outliers(
    series: pd.Series,
    contamination: float = 0.01,
    n_neighbors: int = 20,
    label: str = "Temperature",
    unit: str = "°C",
) -> tuple[Figure, dict[str, float | int], pd.DataFrame]:
    """LOF anomalies on standardised (time, value), the peers' formulation.

    Using time as a second feature makes LOF compare each hour with its
    neighbours in time, so it flags locally unusual spells rather than the
    globally most extreme values.
    """
    values = _as_series(series)
    if len(values) <= n_neighbors:
        raise ValueError(
            f"LOF needs more than n_neighbors={n_neighbors} samples, "
            f"got {len(values)}"
        )

    index = values.index
    assert isinstance(index, pd.DatetimeIndex)
    days = (index - index[0]).total_seconds().to_numpy() / 86400
    features = np.column_stack([days, values.to_numpy(dtype=float)])
    features = StandardScaler().fit_transform(features)

    detector = LocalOutlierFactor(
        n_neighbors=n_neighbors,
        contamination=contamination,
    )
    labels = detector.fit_predict(features)
    scores = -detector.negative_outlier_factor_
    is_outlier = labels == -1

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(values.index, values, linewidth=0.6, label=f"{label} (area mean)")
    if is_outlier.any():
        ax.scatter(
            values.index[is_outlier],
            values.to_numpy()[is_outlier],
            color="#B35A12",
            s=18,
            zorder=3,
            label=f"Anomalies ({int(is_outlier.sum())})",
        )
    ax.set_title(
        f"{label}: {int(is_outlier.sum())} LOF anomalies in {len(values):,} hours "
        f"(contamination={contamination:.1%}, neighbours={n_neighbors})"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel(f"{label} [{unit}]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()

    table = pd.DataFrame(
        {
            "value": values.to_numpy(dtype=float),
            "lof_score": scores,
        },
        index=values.index,
    )
    table = table.loc[is_outlier].sort_values("lof_score", ascending=False)
    table.index.name = "timestamp"

    summary: dict[str, float | int] = {
        "hours": int(len(values)),
        "anomalies": int(is_outlier.sum()),
        "share": float(is_outlier.mean()),
        "n_neighbors": int(n_neighbors),
    }
    return fig, summary, table
