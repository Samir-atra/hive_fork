import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';
import React from 'react';

// Mock Electron window.ipcRenderer
(global as any).window = {
  ipcRenderer: {
    on: () => {},
    off: () => {},
    send: () => {},
    invoke: () => Promise.resolve(),
  },
};

describe('Hive Platform', () => {
  it('renders the HIVE header', () => {
    render(<App />);
    expect(screen.getByText('HIVE')).toBeInTheDocument();
  });

  it('initially shows the Goal Studio module', () => {
    render(<App />);
    expect(screen.getByText('Define your goal.')).toBeInTheDocument();
  });
});
