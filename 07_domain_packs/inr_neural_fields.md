# Domain pack: implicit neural representations / neural fields (state: late 2026)

Only subfield-expert personas receive this. It is what a reviewer who works in this subfield
carries in their head. It is NOT a checklist to apply mechanically: use what your persona would
notice.

## Lines of work an expert knows
- Periodic and other activations: SIREN; Fourier-feature / positional encoding (Tancik et al.);
  Gaussian activations; WIRE (Gabor wavelets); FINER and FINER++ (variable-periodic); INCODE;
  sinc-INR; SPDER; H-SIREN; FM-SIREN; STAF; SL2A-INR; learned or Fourier-series activations;
  KAN-style INRs.
- Frequency, initialization and training: spectral bias and NTK analyses; BACON (band-limited);
  FR-INR (Fourier reparameterized training); TUNER (frequency tuning and robust training of
  sinusoidal networks); FreSh; VI3NR (variance-informed initialization).
- Spatially adaptive or hierarchical: SASNet (spatially adaptive sinusoidal networks), MR-Net and
  multi-resolution networks, NFFB (neural Fourier filter bank), modulated SIREN / FiLM-style
  conditioning, COSMO-INR, FDHO, Neural-ODE INRs (DINR).
- Grid and hybrid: Instant-NGP hash grids, plenoxel / tensor decompositions (TensoRF, K-Planes),
  and other grid+MLP hybrids. Experts ask why a pure MLP is preferable to a hash grid at equal time.
- Tasks: image fitting (Kodak-24, DIV2K), super-resolution and denoising (WIRE-style protocols),
  inpainting, occupancy and SDF (Stanford 3D, Thingi), NeRF (Blender synthetic, LLFF), audio, video,
  INR-based compression (COIN line).

## What reviewers in this subfield have demanded (from 130 real ICLR/NeurIPS reviews, 2025-26)
- A named mechanism beats a sweep of tasks. A five-modality paper was rejected 4/4/4/4 as
  "results are rather minor"; a paper with the same task shape and a clear mechanism was accepted.
  Typical line: "this is just another paper proposing yet another activation for the INR community."
- Overfitting is not generalization. About a third of reviews asked whether fitting PSNR shows
  anything beyond memorization, e.g. held-out pixels or a train/test split, or downstream tasks.
  Typical line: "the experimental protocol is related to pure overfitting rather than true
  test-time performance."
- Compute rather than parameters. Wall-clock time or FLOPs were demanded in about 40% of reviews,
  matched parameters rarely. Typical lines: "one could almost always improve in metrics by
  increasing the complexity of the activation function"; "fairness suggests giving comparison
  algorithms more time".
- Noise floor. PSNR moves several dB with learning rate, init scale or omega; a 1-3 dB win over an
  untuned baseline reads as tuning noise. Experts ask whether every baseline was tuned.
- Kodak has no fixed bar. Published SIREN numbers on Kodak range from about 27 to 38 dB across
  papers. Experts distrust copied numbers and ask how each baseline was run; they ask for peak
  versus final PSNR when training is unstable.
- Theory is expected but often criticized: substitution into known NTK results, disconnected from
  the experiments, heuristics dressed as principles, or only covering SIREN/ReLU but not WIRE/FINER.
- Stale baselines. SIREN + WIRE + Gauss alone is now called dated; experts expect several of FINER,
  INCODE, SL2A, sinc, FreSh, TUNER, a hash grid, and the closest spatially adaptive method.
- Small benchmarks. Kodak's 24 images get called small; DIV2K or larger and higher resolution
  are expected for strong claims.

- Corpus profile (60 real INR reviews, ICLR/NeurIPS 2024-2026): the most common INR complaint is
  limited scope (65%: "only fitting", "no NeRF or inverse problems", "one type of neural field"),
  then small benchmarks (40%). Novelty is raised less often than in 3D papers (27% vs 49%).
  Reviewers name "the most recent same-family method, or the method the submission builds on";
  names seen in real INR reviews: FINER/FINER++, WIRE, SPDER, FreSh, TUNER, BACON, VI3NR, MFN,
  Fourier features, Instant-NGP, DVGO, ACORN, NGLOD, functa, MINER, NeRV, STRAINER.

## Things an expert checks quickly
- Is the parameter count comparable, AND is the time per step or total time reported?
- Are learning rates and omega/scale tuned per baseline, or copied from defaults?
- Are numbers for baselines lower than in the baselines' own papers? If so, why?
- Is "frequency" used precisely (instantaneous frequency vs Fourier spectrum vs activation period)?
- Do NeRF numbers use the standard Blender split and resolution? Are they in the range of current
  methods, or far below grid-based methods (then why should anyone use it)?
- Is the claimed mechanism shown by an intervention (ablation at equal budget), or only by a
  correlation plot?
