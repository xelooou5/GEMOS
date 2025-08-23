#!/bin/bash
# This script organizes the GEM OS project files, cleaning up the backup directory
# and establishing a clean, unified structure.
# Run it from the root of your project (e.g., /home/oem/gem/).

set -e # Exit immediately if a command exits with a non-zero status.
echo "💎 Starting GEM OS project organization..."

# --- Define Directories ---
SOURCE_DIR="backup_before_encoding_fix"
CORE_DIR="core"
FEATURES_DIR="features"
CONFIG_DIR="config"

# --- Ensure Target Directories Exist ---
mkdir -p "$CORE_DIR" "$FEATURES_DIR" "$CONFIG_DIR"
echo "✅ Ensured '$CORE_DIR/', '$FEATURES_DIR/', and '$CONFIG_DIR/' directories exist."

# --- List of actual project files to move ---
CORE_FILES=(
    "audio_system.py" "command_executor.py" "llm_handler.py"
    "plugins.py" "storage.py" "stt_module.py" "tts_module.py"
)
FEATURES_FILES=(
    "accessibility_tools.py" "learning_tools.py"
)
# The one true config logic file
CONFIG_LOGIC_FILE="config.py"

# --- List of extraneous files from other libraries to delete ---
JUNK_FILES=(
    "__init__.py" "arguments.py" "audio.py" "default.py" "espeak.py" "features.py"
    "files.py" "input_json_delta.py" "language.py" "local.py" "model.py"
    "overrides.py" "requirements.py" "system.py" "text_delta.py" "translate.py"
    "voice.py" "config_manager.py" "parse.py" "error.py" "output.py" "torch.py"
    "win32.py"
)

# --- Function to move files safely ---
move_file() {
    local file="$1"
    local dest_dir="$2"
    if [ -f "$SOURCE_DIR/$file" ]; then
        # Force move and overwrite if the file already exists in the destination
        mv -f "$SOURCE_DIR/$file" "$dest_dir/"
        echo "  - Moved $file to $dest_dir/"
    else
        echo "  - ⚠️  Warning: $file not found in $SOURCE_DIR, skipping."
    fi
}

# --- Delete Extraneous Files ---
echo "🗑️  Deleting extraneous library files from '$SOURCE_DIR/'..."
for file in "${JUNK_FILES[@]}"; do
    if [ -f "$SOURCE_DIR/$file" ]; then
        rm "$SOURCE_DIR/$file"
        echo "  - Deleted junk file: $file"
    fi
done

# --- Move Core Files ---
echo "🧠 Moving core system files to '$CORE_DIR/'..."
for file in "${CORE_FILES[@]}"; do
    move_file "$file" "$CORE_DIR/"
done

# --- Move Feature Files ---
echo "✨ Moving feature files to '$FEATURES_DIR/'..."
for file in "${FEATURES_FILES[@]}"; do
    move_file "$file" "$FEATURES_DIR/"
done

# --- Unify Configuration ---
echo "⚙️  Unifying configuration system..."
# Delete the old deprecated compatibility layer
if [ -f "core/config_manager.py" ]; then
    rm "core/config_manager.py"
    echo "  - Deleted deprecated core/config_manager.py"
fi
# Delete the confusing root-level config file
if [ -f "config.json" ]; then
    rm "config.json"
    echo "  - Deleted confusing root-level config.json"
fi
# Move the good config logic file and rename it
if [ -f "$SOURCE_DIR/$CONFIG_LOGIC_FILE" ]; then
    mv "$SOURCE_DIR/$CONFIG_LOGIC_FILE" "core/config_manager.py"
    echo "  - Moved and renamed the new definitive 'core/config_manager.py'"
else
    echo "  - ⚠️  Warning: Definitive config logic file '$CONFIG_LOGIC_FILE' not found in $SOURCE_DIR."
fi

# --- Final Cleanup ---
echo "🧹 Final cleanup..."
if [ -d "$SOURCE_DIR" ] && [ -z "$(ls -A "$SOURCE_DIR")" ]; then
    rmdir "$SOURCE_DIR"
    echo "✅ Removed the now-empty '$SOURCE_DIR/' directory."
else
    echo "⚠️ '$SOURCE_DIR/' is not empty. Please review its contents before deleting it manually."
fi

echo "🎉 Project organization complete! Your file structure is now clean and ready for greatness."