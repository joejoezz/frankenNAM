# Shared helpers for build_*.sh. Source after env.sh.
mkdir -p "$NAM_WORK/logs" "$NAM_EXEC"

# Copy the upstream tree to /opt/nam/work/src once (never edit upstream in place).
stage_src() {
  if [ ! -f "$NAM_SRC/.staged" ]; then
    mkdir -p "$NAM_SRC"
    rsync -a --exclude .git "$NAM_UPSTREAM/" "$NAM_SRC/"
    git -C "$NAM_UPSTREAM" rev-parse HEAD > "$NAM_SRC/.staged"
  fi
  echo "upstream commit $(cat "$NAM_SRC/.staged")"
}

# Apply build/patches/<prefix>-*.patch (paths relative to $NAM_SRC), skipping ones already in.
apply_src_patches() {
  local f
  for f in "$BUILD_DIR"/patches/"$1"-*.patch; do
    [ -e "$f" ] || continue
    if patch -d "$NAM_SRC" -p1 -R --dry-run -s -f < "$f" >/dev/null 2>&1; then
      echo "already applied $(basename "$f")"
    else
      patch -d "$NAM_SRC" -p1 -s -f < "$f"; echo "applied $(basename "$f")"
    fi
  done
}

print_versions() {
  echo "== toolchain ($TOOLCHAIN, $ARCH)"
  if [ "$TOOLCHAIN" = gnu ]; then
    gfortran --version | head -1; gcc --version | head -1
    echo "mpif90 -> $(mpif90 -show | cut -d" " -f1), $(mpirun --version 2>&1 | head -1)"
  else
    ifort --version 2>&1 | grep -v remark | head -1; icx --version | head -1
    echo "mpiifort -> $(mpiifort -show | cut -d" " -f1), mpiicc -> $(mpiicc -show | cut -d" " -f1), Intel MPI $IMPI_VER"
  fi
  echo "== libraries"; cat "$LIBS_ROOT"/*/.built 2>/dev/null
}
