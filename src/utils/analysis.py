"""Analysis helpers shared by the CA3 notebook and the Streamlit pages.

One implementation is used by both artifacts:

* ``notebooks/CA3/Proj-P3.py`` imports the four public functions for the
  executed hand-in notebook;
* ``src/streamlit/pages/reservoir_analysis.py`` and ``weather_quality.py``
  import the same functions for the two CA3 pages.

The functions are deliberately independent of Streamlit and of any file paths:
they take a pandas Series with a DatetimeIndex and return a Matplotlib figure
plus plain pandas objects. The caller decides where the data come from and how
the result is rendered.

CRS: none. Every function here works on an area-mean time series, never on
coordinates. The spatial work (EPSG:25833 -> EPSG:3035 sampling -> EPSG:4326
for the weather API) lives in ``notebooks/CA3``; see ``docs/CA3/crs.md``.
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

MAD_TO_SD = 1.4826


def _as_series(series: pd.Series) -> pd.Series:
    """Return a sorted float series with a DatetimeIndex and no gaps."""
    values = pd.Series(series).astype(float).interpolate().sort_index()
    if not isinstance(values.index, pd.DatetimeIndex):
        raise TypeError("series must have a DatetimeIndex")
    if values.empty:
        raise ValueError("series is empty")
    return values


def robust_sigma(values: np.ndarray) -> float:
    """MAD-based standard deviation (1.4826 * median absolute deviation)."""
    centre = np.median(values)
    return float(MAD_TO_SD * np.median(np.abs(values - centre)))


def _satv_from_k(values: np.ndarray, k: int) -> np.ndarray:
    """High-pass part of ``values`` after zeroing the first ``k`` DCT coefficients."""
    coefficients = np.asarray(dct(values, norm="ortho"), dtype=float)
    coefficients[: max(0, min(k, len(coefficients)))] = 0.0
    return np.asarray(idct(coefficients, norm="ortho"), dtype=float)


def satv_from_dct(series: pd.Series, cutoff_fraction: float = 0.02) -> np.ndarray:
    """Return the DCT high-pass part of ``series`` (the SATV).

    Kept as the low-level helper used by the tests and by ``spc_outliers``;
    the public SPC interface expresses the cut-off in cycles per year.
    """
    if not 0 <= cutoff_fraction < 1:
        raise ValueError("cutoff_fraction must be in [0, 1)")
    values = _as_series(series).to_numpy(dtype=float)
    return _satv_from_k(values, int(len(values) * cutoff_fraction))


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

    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
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
    axes[-1].set_xlabel("Date")
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
    lower_bound: float | None = None,
) -> tuple[Figure, dict[str, float | int], pd.DataFrame]:
    """SPC outliers from a DCT high-pass (SATV) with robust limits.

    ``cutoff_per_year`` removes variations slower than that many cycles per
    year (12 ≈ one month). The limits follow the slow seasonal baseline:
    ``baseline + median(SATV) ± n_std * robust_sigma(SATV)``. The SATV itself
    is used only for the limits and the outlier flags, never plotted.

    ``lower_bound`` optionally floors the lower limit; precipitation passes 0.
    Returns the figure, a summary dictionary and the outlier table.
    """
    values = _as_series(series)
    if len(values) < 3:
        raise ValueError("Need at least three observations")
    if not np.isfinite(cutoff_per_year) or cutoff_per_year <= 0:
        raise ValueError("cutoff_per_year must be positive")
    if not np.isfinite(n_std) or n_std <= 0:
        raise ValueError("n_std must be positive")

    index = values.index
    assert isinstance(index, pd.DatetimeIndex)
    years = (index[-1] - index[0]).total_seconds() / (365.25 * 24 * 3600)
    # DCT coefficient k represents k/2 cycles over the whole series.
    k = int(round(2 * cutoff_per_year * max(years, 1e-6)))
    k = max(1, min(k, len(values) - 1))

    data = values.to_numpy(dtype=float)
    satv = _satv_from_k(data, k)
    baseline = data - satv
    centre_offset = float(np.median(satv))
    sigma = robust_sigma(satv)

    centre = baseline + centre_offset
    upper = centre + n_std * sigma
    lower = centre - n_std * sigma
    if lower_bound is not None:
        lower = np.maximum(lower, lower_bound)

    is_outlier = (data > upper) | (data < lower)
    table = pd.DataFrame(
        {
            "value": data[is_outlier],
            "satv": satv[is_outlier],
            "lower": lower[is_outlier],
            "upper": upper[is_outlier],
        },
        index=index[is_outlier],
    )
    table.index.name = "timestamp"

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(index, data, linewidth=1.0, label="Observed")
    ax.plot(index, centre, color="tab:gray", linestyle=":", label="Baseline")
    ax.plot(index, upper, color="tab:red", linestyle="--", label="SPC upper")
    ax.plot(index, lower, color="tab:red", linestyle="--", label="SPC lower")
    ax.scatter(
        table.index,
        table["value"],
        color="tab:red",
        s=35,
        zorder=3,
        label=f"Outliers ({len(table)})",
    )
    ax.set_title(
        f"SPC on {label} "
        f"(DCT cut-off={cutoff_per_year:g} cycles/year, ±{n_std:g}σ, "
        f"σ_robust={sigma:.3g})"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel(f"{label} [{unit}]" if unit else label)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()

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
    """LOF anomalies on standardised (time, value).

    Time is included as a feature so an observation is compared with its
    neighbours in time, not only with the global distribution. The
    ``contamination`` parameter sets the expected anomaly share (default 1 %).
    """
    values = _as_series(series)
    if len(values) <= n_neighbors:
        raise ValueError(
            f"LOF needs more than n_neighbors={n_neighbors} samples, "
            f"got {len(values)}"
        )
    if not 0 < contamination <= 0.5:
        raise ValueError("contamination must be in (0, 0.5]")

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

    table = pd.DataFrame(
        {
            "value": values.to_numpy(dtype=float)[is_outlier],
            "lof_score": scores[is_outlier],
        },
        index=index[is_outlier],
    )
    table.index.name = "timestamp"
    table = table.sort_values("lof_score", ascending=False)

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(index, values, linewidth=1.0, label="Observed")
    ax.scatter(
        table.index,
        table["value"],
        color="tab:orange",
        s=35,
        zorder=3,
        label=f"Anomalies ({len(table)})",
    )
    ax.set_title(
        f"LOF anomalies in {label} "
        f"(contamination={contamination:.0%}, n_neighbors={n_neighbors})"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel(f"{label} [{unit}]" if unit else label)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()

    summary: dict[str, float | int] = {
        "hours": int(len(values)),
        "anomalies": int(is_outlier.sum()),
        "share": float(is_outlier.mean()),
        "n_neighbors": int(n_neighbors),
        "contamination": float(contamination),
    }
    return fig, summary, table
