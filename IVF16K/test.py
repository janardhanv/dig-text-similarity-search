import os
import sys
from time import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from digtextsimilaritysearch.indexer.IVF16K_index_handler \
    import DeployIVF16K
from digtextsimilaritysearch.vectorizer.sentence_vectorizer \
    import SentenceVectorizer
from digtextsimilaritysearch.storage.es_adapter \
    import ESAdapter
from digtextsimilaritysearch.process_documents.document_processor \
    import DocumentProcessor


# Paths
cwd = os.getcwd()
print('cwd: {}'.format(cwd))
emb_dir = os.path.join(cwd, 'data/vectorized_sage_news/new_2018-08-from07to13')
index_dir = os.path.join(cwd, 'saved_indexes/IVF16K_indexes')
subindex_dir = os.path.join(index_dir, 'subindexes')
dt_sim_dir = '/lfs1/dig_text_sim'


# Init
t_init0 = time()
deployable = os.path.join(index_dir, 'populatedIVF16384.index')
idx = DeployIVF16K(path_to_deployable_index=deployable)

sv = SentenceVectorizer()

logstash_path = '/lfs1/dig_text_sim/IVF16K_logstash_input.jl'
es = ESAdapter(logstash_file_path=logstash_path)

table = 'dig-text-similarity-search-IVF16K'
dp = DocumentProcessor(indexer=idx, vectorizer=sv,
                       storage_adapter=es, table_name=table)
t_init1 = time()
print('\n\nInitialized in {:0.2f}s\n'.format(t_init1-t_init0))


# Test Queries
q0 = 'Before 8 September 2018, will the UK request an extension ' \
     'to Article 50 for leaving the EU?'

q1 = 'Will China execute or be targeted in an acknowledged ' \
     'national military attack before 1 September 2018?'

q2 = 'Will the WHO declare a Public Health Emergency of ' \
     'International Concern (PHEIC) before 1 September 2018?'

q3 = 'Will UK Prime Minister Theresa May announce her resignation, ' \
     'lose a confidence vote, or otherwise vacate her office ' \
     'before 8 September 2018?'

q4 = 'Will American pastor Andrew Brunson leave Turkey ' \
     'before 8 September 2018?'

queries = [q0, q1, q2, q3, q4]


# K
k_search = 50
k_report = 10


# Run it
all_results = list()
time_stamps = list()
for i, q in enumerate(queries, start=1):
    t_0 = time()
    results = dp.query_text(str_query=q, k=k_search)
    print(results)
    print(type(results))
    all_results.append(results)
    t_diff = time() - t_0
    time_stamps.append(t_diff)
    print('Query {} completed in {:0.4f}s'.format(i, t_diff))


# Check time for batch search
t_batch = time()
_ = dp.query_text(str_query=queries, k=k_search)
t_batch = time() - t_batch
print('Batch query completed in {:0.4f}s'.format(t_batch))

print(len(all_results))
print(len(all_results[0]))

# Report it
base_url = 'http://dig:dIgDiG@mydig-sage-internal.isi.edu/es/sage_news/ads/'
for i, (q, rs, t) in enumerate(zip(queries, all_results, time_stamps), start=1):
    file_name = 'IVF16K_query_test_' + str(i) + '_results.txt'
    file_path = os.path.join(cwd, file_name)

    try:
        with open(file_path, 'x') as f:
            f.write('Query: {}\n'.format(q))
            f.write('Results for single query gathered in: {:0.4f}s\n'.format(t))
            f.write('Compare: Results for {} queries batch-gathered in '
                    '{:0.4f}s\n\n\n'.format(len(queries), t_batch))
            j = 1
            doc_ids = set()
            for r in rs:
                if j <= k_report and r['doc_id'] not in doc_ids:
                    j += 1
                    doc_ids.add(r['doc_id'])
                    f.write('  Result: {}\n'.format(j))
                    f.write('  Difference Score: {:0.5f}\n'.format(r['score']))
                    f.write('  Text: {}\n'.format(r['sentence'].replace('\n', ' ')))
                    f.write('  Document ID: {}\n'.format(r['doc_id']))
                    f.write('  Link to cdr_doc: {}{} \n\n'.format(base_url, r['doc_id']))

    except FileExistsError:
        print('File already exists: {}'.format(file_path))
