import bundleAnalyzer from '@next/bundle-analyzer';
import config from './next.config.ts';

const withBundleAnalyzer = bundleAnalyzer({ enabled: process.env.ANALYZE === 'true' });

// Node 24 loads the shared, erasable TypeScript config without a build step.
export default withBundleAnalyzer(config);
