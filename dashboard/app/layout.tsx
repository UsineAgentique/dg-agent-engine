import './globals.css';

export const metadata = {
  title: 'Amal-DG Control Center',
  description: 'Dashboard de surveillance autonome des agents',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body style={{ margin: 0, padding: 0, backgroundColor: '#020617' }}>{children}</body>
    </html>
  );
}
