
def compute_final_score(hard_matches, semantic_sim, weights={'hard':0.6,'soft':0.4}):
    # hard_matches: list of {'skill','score'} where score 0-100 fuzzy ratio
    if len(hard_matches)==0:
        hard_score = 0
    else:
        hard_score = sum([m['score'] for m in hard_matches]) / (len(hard_matches) * 100) * 100
    soft_score = semantic_sim * 100
    final = hard_score * weights.get('hard',0.6) + soft_score * weights.get('soft',0.4)
    final = max(0, min(100, final))
    if final >= 75:
        verdict = 'High'
    elif final >= 50:
        verdict = 'Medium'
    else:
        verdict = 'Low'
    # missing skills = must with score < 50
    missing = [m['skill'] for m in hard_matches if m['score'] < 50]
    return {'score': round(final,2), 'verdict': verdict, 'missing': missing, 'hard_score': round(hard_score,2), 'soft_score': round(soft_score,2)}
