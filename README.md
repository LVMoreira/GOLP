
# Modelling short pulse laser-solid interaction
---

**Affiliation:** Group of Lasers and Plasmas (GOLP), IPFN, IST

**Code:** MULTI-fs (1D Hydrodynamic Simulation - adapted from MULTI-IFE for femtosecond pulses)

**Material:** Titanium (Ti)

## 1. Project Overview

This repository contains configuration files, simulation outputs, and post-processing scripts for analyzing the interaction of high-intensity, short-pulse lasers with solid Titanium targets.

**Simulation Code:** The study utilizes MULTI-fs, a specialized variant of the MULTI code family tailored for the femtosecond and picosecond regimes.
- Lineage: It is derived from MULTI-IFE (Inertial Fusion Energy), which itself is based on the original MULTI (MULTI-group Radiation Transport) code.
- Method: It is a 1-D Radiation-Hydrodynamics code operating in a Lagrangian frame, meaning the computational grid moves with the fluid. This allows for precise tracking of steep density gradients and material interfaces during expansion.

The primary goal is to simulate the hydrodynamic evolution of the target, specifically tracking:

- Electron and Ion Temperatures (Te​,Ti​)

- Density profiles (ρ)

- Shock wave propagation

- Ionization dynamics

These simulations are performed using MULTI-fs and benchmarked against/compared with Medusa simulations and experimental data.

## 2. Simulation Procedures:

All simulation data was obtained by running MULTI-fs on an HPC cluster (Deucalion). The input files are provided in the repository (fort.12), along with the respective output file (fort.11). Different approaches were implemented in order to obtain simulation results that agree with experimental data. 

### Pulse_Wkb Approach:
At first, the pulse was simulated using the wkb approximation. However, after comparing results with different simulation algorithms, some inconsistencies were detected (very early forming shockwave, extremelly high ionic and electronic temperatures).

**Sample parameter block:**
´´´&pulse_wkb
  inter=1,        ! from right
  wl=0.8,          ! microns (800 nm)
  pimax=4.2e19,    ! 1e15 W/cm^2 = 1e22 erg/s/cm^2
  pitime=5.0e-14,  ! 50 fs FWHM
  itype=1,         ! sin^2 envelope
  delta=1.0
/´´´

### Maxwell solver approach:
In order to achieve more accurate simulation results, the maxwell solver was used. This 







## . Directory Structure

The project follows a relative path structure to ensure reproducibility across different machines (handled via Python's pathlib).

├── inputs/                 # MULTI-fs input files (*.in)
├── eos/                    # Equation of State tables (e.g., SESAME, QEOS for Ti)
├── runs/                   # Simulation output data
│   └── Medusa/
│       └── MULTI/
│           └── 0d42e13Wcm2_5ps/   # Specific run case
│               ├── fort.11        # MULTI time-step data
│               └── Med103_...txt  # Medusa comparison data
├── scripts/                # Python post-processing scripts
│   ├── load_data.py        # Data parsing logic
│   └── plot_profiles.py    # Matplotlib visualization
├── notebooks/              # Jupyter notebooks for interactive analysis
└── README.md




