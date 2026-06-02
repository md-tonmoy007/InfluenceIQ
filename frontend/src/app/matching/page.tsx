import '../matching.css';
import MatchingAnimation from '@/components/briefs/MatchingAnimation';
import { Suspense } from 'react';

export default function MatchingPage() {
  return (
    <Suspense fallback={<div style={{ background: '#06070d', height: '100vh' }} />}>
      <MatchingAnimation />
    </Suspense>
  );
}
