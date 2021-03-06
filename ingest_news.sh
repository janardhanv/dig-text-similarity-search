#!/usr/bin/env bash

## Prep
DT_SIM="/faiss/dig-text-similarity-search/"
PREPROC="${DT_SIM}py_scripts/preprocessing/"
SERVICE="${DT_SIM}py_scripts/service/"

# Activate conda env
ACTIVATE="/home/ubuntu/anaconda3/bin/activate"
cd "$DT_SIM" && . "$ACTIVATE" dt_sim

# Constant working dirs
NEWS_DIR="/faiss/sage_news_data/raw/LN_WLFilt_extractions_IN/"
DONE_DIR="/faiss/sage_news_data/raw/LN_WLFilt_extractions_OUT/"
PUB_DATES="/faiss/sage_news_data/pub_date_split/"
DAILY_DIR="/faiss/faiss_index_shards/tmp_daily_ingest/"

MAIN_IDXS="/faiss/faiss_index_shards/deployment_full/"
TMP_IDXS="/green_room/idx_deploy_B/"

echo "Main: $MAIN_IDXS has $(ls "$MAIN_IDXS"*.index | wc -l) shards"
echo "Tmp: $TMP_IDXS has $(ls "$TMP_IDXS"*.index | wc -l) shards
"

# Process 1 file per call to shell script
FILE=$(ls "${NEWS_DIR}" | head -1)
if [[ -z "$FILE" ]]; then
    printf "Nothing to process... \n"
    exit 1
else
    printf "Processing $FILE \n"
fi

# Get extraction ISO date as YYYY, MM, & DD
YYYYMMDD=$(echo "$FILE" | grep -Eo "[0-9]{4}\-[0-9]{2}\-[0-9]{2}")
YYYY=$(echo "$YYYYMMDD" | cut -d "-" -f1)
MM=$(echo "$YYYYMMDD" | cut -d "-" -f2)
DD=$(echo "$YYYYMMDD" | cut -d "-" -f3)

echo "  * Year: $YYYY   * Month: $MM    * Day: $DD
"

# New working dirs
DATE_SPLIT="${PUB_DATES}${YYYY}_extraction_${MM}-${DD}/"
DAILY_IDXS="${DAILY_DIR}${YYYY}_indexes_${MM}-${DD}/"
# Fail and exit if dirs exist (Indication that file has already been processed)
if [[ -d "$DATE_SPLIT" ]] || [[ -d "$DAILY_IDXS" ]]; then
    printf "$FILE has already been processed! \nExiting... \n"
    exit 1
else
    mkdir "$DATE_SPLIT"
    mkdir "$DAILY_IDXS"
fi


## Split
echo "Splitting articles in $FILE by publication dates between
$(date -d "-40 days $YYYYMMDD" -I) and $YYYYMMDD"

python -u "${PREPROC}sort_by_pub_date.py" "${NEWS_DIR}${FILE}" "$DATE_SPLIT" \
-i "$(date -d "-40 days $YYYYMMDD" -I)" -f "$YYYYMMDD";



## Vectorize
n_shards=$(ls "$DATE_SPLIT"*.jl | wc -l)

# Exit if there is nothing to vectorize
if [[ "$n_shards" > 0 ]]; then
    printf "\nFound $n_shards day(s) of news to vectorize \n"
else
    echo "Nothing to process... Exiting"
    exit 1
fi

for i in `seq 1 "$n_shards"`; do
	printf "\n\nStarting $i/$n_shards @ $(date)\n";
	python -u py_scripts/preprocessing/prep_shard.py "$DATE_SPLIT" "$DAILY_IDXS" \
	-p "${DATE_SPLIT}progress.txt" -b "${DT_SIM}base_indexes/USE_large_base_IVF4K_15M.index" \
	-l -n 128 -v -t 2;      # Previously written to take dirs as inputs, not files
done



## Zip new indexes into deployed indexes
# Switch to tmp service
kill -15 $(ps -ef | grep "[s]imilarity_server" | awk '{print $2}'); sleep 1;
python -u "${SERVICE}similarity_server.py" "$TMP_IDXS" -l -c 6 &

# Zip-merge into main indexes
# Note: echo "n" prevents deleting new indexes before second zip
echo "n" | python -u "${PREPROC}consolidate_shards.py" \
"$DAILY_IDXS" "$MAIN_IDXS" --zip -p "zip_to_${MM}${DD}" -t 2;

# Switch back to main service
LOG_FILE="/faiss/dig-text-similarity-search/logs/service/deploy_${MM}${DD}.out"
kill -15 $(ps -ef | grep "[s]imilarity_server" | awk '{print $2}'); sleep 1;
python -u "${SERVICE}similarity_server.py" "$MAIN_IDXS" -l -c 6 >> "$LOG_FILE" &

# Second zip-merge into tmp indexes
# Note: echo "y" will delete new indexes
echo "y" | python -u "${PREPROC}consolidate_shards.py" \
"$DAILY_IDXS" "$TMP_IDXS" --zip -p "zip_to_${MM}${DD}" -t 2;



## Save backups to S3
echo "
Syncing s3..."
aws s3 sync "${MAIN_IDXS}" s3://lexisnexis-news-incremental"${MAIN_IDXS}" --delete


## Cleanup
rm "$DATE_SPLIT"*.jl "$DATE_SPLIT"*/*.jl
rmdir "${DATE_SPLIT}old_news" "${DATE_SPLIT}date_error"
mv "${NEWS_DIR}${FILE}" "${DONE_DIR}${FILE}"

echo "

Finished @ $(date)
"
exit 1
