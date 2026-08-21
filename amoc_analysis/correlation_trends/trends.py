"""Linear trends and their significance for autocorrelated series.

Worked helper: :func:`fit_trend`. Student stub: :func:`trend_with_significance`.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
from numpy.typing import ArrayLike
from scipy import stats

from .correlation import effective_dof


class TrendResult(NamedTuple):
    """Result of :func:`trend_with_significance`.

    Attributes
    ----------
    slope, intercept : float
        Least-squares fit coefficients (``x ~ slope * t + intercept``).
    se : float
        Naive OLS standard error of the slope (assumes independent residuals).
    se_eff : float
        Standard error inflated for autocorrelation, ``se * sqrt(N / N_eff)``.
    p_naive, p_eff : float
        Two-sided p-values for ``slope = 0`` using ``se`` (with ``N - 2`` d.o.f.)
        and ``se_eff`` (with ``N_eff - 2`` d.o.f.) respectively.
    n_eff : float
        Effective sample size ``N / (1 + 2 sum rho_k)`` from the residuals.
    t_naive, t_eff : float
        Slope in units of its standard error (``slope / se`` and ``slope / se_eff``)
        -- how many sigma the slope sits from zero. Significant at 95% needs
        ``|t| > ~1.96``.
    """

    slope: float
    intercept: float
    se: float
    se_eff: float
    p_naive: float
    p_eff: float
    n_eff: float
    t_naive: float
    t_eff: float


def fit_trend(t: ArrayLike, x: ArrayLike) -> tuple[float, float]:
    """Least-squares straight-line fit.

    Parameters
    ----------
    t : array_like
        Predictor (e.g. time).
    x : array_like
        Response series.

    Returns
    -------
    slope, intercept : float
        Coefficients of ``x ~ slope * t + intercept``.
    """
    slope, intercept = np.polyfit(np.asarray(t, float), np.asarray(x, float), 1)
    return float(slope), float(intercept)


def trend_with_significance(t: ArrayLike, x: ArrayLike, dt: float) -> TrendResult:
    """Slope, its standard error, ``slope/SE``, and autocorrelation-aware p-values.

    The naive standard error assumes independent residuals. For a red-noise
    series that is optimistic: neighbouring residuals are correlated, so the
    record carries fewer independent samples than ``N``. The honest version
    replaces ``N`` by the effective sample size ``N_eff`` derived from the
    two-sided integral timescale of the residuals, inflating the SE by
    ``sqrt(N / N_eff)``.

    Parameters
    ----------
    t : array_like
        Predictor (time), same units implied by ``dt``.
    x : array_like
        Response series.
    dt : float
        Sample spacing (present for interface symmetry; ``N_eff`` here is a
        sample count and does not depend on ``dt``).

    Returns
    -------
    TrendResult
        Slope, intercept, naive and effective SE, p-values, ``N_eff``, and the
        ``slope/SE`` ratios ``t_naive`` and ``t_eff``.

    Notes
    -----
    ``sigma`` in ``slope/SE`` is the standard error *of the slope itself* -- how
    much the fitted slope would wobble on resampling -- not the scatter of the
    data about the line. Significant at 95% means ``|slope| > ~1.96 * SE``.
    """
    # --- Mask NaNs (in either t or x) before any computation ---
    mask = ~np.isnan(t) & ~np.isnan(x)
    if not np.all(mask):
        n_dropped = np.sum(~mask)
        n_total = t.size
        print(f"trend_with_significance: dropping {float(n_dropped)}/{n_total} NaN samples")
    t = t[mask]
    x = x[mask]
    N = t.size

    if N < 3:
        raise ValueError(
            f"Not enough valid (non-NaN) samples to fit a trend: N={N} after masking"
        )

    # --- Fit ---
    slope, intercept = fit_trend(t, x)
    slope, intercept = float(slope), float(intercept)

    resid = x - (slope * t + intercept)

    # --- Naive OLS standard error of the slope ---
    dof_naive = N - 2
    resid_var = np.sum(resid**2) / dof_naive
    ss_t = np.sum((t - t.mean())**2)
    se_naive = float(np.sqrt(resid_var / ss_t))

    # --- Effective sample size from residual autocorrelation ---
    n_eff = float(effective_dof(resid, dt))

    # --- Inflate SE for lost independence ---
    se_eff = float(se_naive * np.sqrt(N / n_eff))

    # --- t-statistics ---
    t_naive =float( slope / se_naive)
    t_eff = float(slope / se_eff
)
    # --- p-values ---
    # naive: dof = N - 2 (standard OLS)
    p_naive = float(2 * stats.t.sf(np.abs(t_naive), df=dof_naive))
    # honest: dof based on effective sample size
    dof_eff = max(n_eff - 2, 1)  # guard against n_eff < 2
    p_eff = float(2 * stats.t.sf(np.abs(t_eff), df=dof_eff)
)
    return TrendResult(
        slope=slope,
        intercept=intercept,
        se=se_naive,
        se_eff=se_eff,
        t_naive=t_naive,
        t_eff=t_eff,
        p_naive=p_naive,
        p_eff=p_eff,
        n_eff=n_eff,
    )
