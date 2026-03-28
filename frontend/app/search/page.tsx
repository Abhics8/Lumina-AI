'use client';

import { useState } from 'react';
import Image from 'next/image';
import { Sparkles, Loader2, Search } from 'lucide-react';
import Link from 'next/link';
import { ImageUpload } from '@/components/search/image-upload';
import { BoundingBoxCanvas } from '@/components/search/bounding-box-canvas';
import { SearchResults } from '@/components/search/search-results';
import { apiClient } from '@/lib/api-client';
import type { DetectionResult, SearchResult } from '@/types/api';

export default function SearchPage() {
    const [isDetecting, setIsDetecting] = useState(false);
    const [isSearching, setIsSearching] = useState(false);
    const [results, setResults] = useState<DetectionResult[]>([]);
    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [searchQuery, setSearchQuery] = useState('');

    const handleTextSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!searchQuery.trim()) return;

        setIsSearching(true);
        setError(null);
        setResults([]);
        setSearchResults([]);
        setImagePreview(null);
        setSelectedFile(null);

        try {
            const response = await apiClient.searchByText(searchQuery);
            setSearchResults(response || []);
        } catch (err) {
            setError('Failed to search. Please try again.');
            console.error(err);
        } finally {
            setIsSearching(false);
        }
    };

    const handleImageSelect = async (file: File) => {
        setIsDetecting(true);
        setError(null);
        setResults([]);
        setSearchResults([]);
        setSelectedFile(file);
        setSearchQuery('');

        // Create preview URL for bounding box canvas
        const reader = new FileReader();
        reader.onloadend = () => {
            setImagePreview(reader.result as string);
        };
        reader.readAsDataURL(file);

        try {
            const response = await apiClient.detectObjects(file);
            setResults(response.detections || []);
        } catch (err) {
            setError('Failed to detect objects. Please try again.');
            console.error(err);
        } finally {
            setIsDetecting(false);
        }
    };


    const handleSearchSimilar = async (detection: DetectionResult) => {
        if (!selectedFile) return;

        setIsSearching(true);
        setError(null);

        try {
            const response = await apiClient.searchSimilar(selectedFile, detection.box);
            setSearchResults(response.results || []);
        } catch (err) {
            setError('Failed to search for similar products. Please try again.');
            console.error(err);
        } finally {
            setIsSearching(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
            {/* Navigation */}
            <nav className="border-b border-white/10 backdrop-blur-sm">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <Link href="/" className="flex items-center gap-2">
                            <Sparkles className="w-6 h-6 text-purple-400" />
                            <span className="text-xl font-bold text-white">Lumina AI</span>
                        </Link>
                    </div>
                </div>
            </nav>

            {/* Main Content */}
            <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <div className="text-center mb-12">
                    <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
                        Visual Search
                    </h1>
                    <p className="text-xl text-gray-300">
                        Upload an image to detect fashion items and find similar products
                    </p>
                </div>

                {/* Text Search Section */}
                <div className="max-w-2xl mx-auto mb-12">
                    <form onSubmit={handleTextSearch} className="relative">
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search for fashion items (e.g., 'summer floral dress')..."
                            className="w-full px-6 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all pr-12"
                        />
                        <button
                            type="submit"
                            disabled={isSearching || !searchQuery.trim()}
                            className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-purple-600 hover:bg-purple-700 text-white rounded-full disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <Search className="w-5 h-5" />
                        </button>
                    </form>
                    <div className="mt-4 flex items-center justify-center gap-4 text-sm text-gray-400">
                        <span className="h-px w-12 bg-white/10"></span>
                        <span>OR</span>
                        <span className="h-px w-12 bg-white/10"></span>
                    </div>
                </div>

                {/* Upload Section */}
                <div className="mb-12">
                    <ImageUpload onImageSelect={handleImageSelect} />

                    {/* Demo Examples */}
                    <div className="mt-8">
                        <p className="text-gray-400 mb-4 text-sm font-medium uppercase tracking-wider text-center">
                            Or try with an example
                        </p>
                        <div className="flex flex-wrap justify-center gap-4">
                            {[
                                {
                                    label: 'Red Sneakers',
                                    url: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&q=80',
                                    filename: 'red-sneakers.jpg'
                                },
                                {
                                    label: 'Denim Jacket',
                                    url: 'https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=400&q=80',
                                    filename: 'denim-jacket.jpg'
                                },
                                {
                                    label: 'Leather Bag',
                                    url: 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400&q=80',
                                    filename: 'leather-bag.jpg'
                                }
                            ].map((example, idx) => (
                                <button
                                    key={example.label}
                                    onClick={async () => {
                                        try {
                                            setIsDetecting(true);
                                            // Fetch the image and convert to File
                                            const res = await fetch(example.url);
                                            const blob = await res.blob();
                                            const file = new File([blob], example.filename, { type: 'image/jpeg' });
                                            await handleImageSelect(file);
                                        } catch (err) {
                                            console.error('Failed to load example', err);
                                            setError('Failed to load example image. Please try again.');
                                            setIsDetecting(false);
                                        }
                                    }}
                                    className="group relative overflow-hidden rounded-xl w-32 h-32 border border-white/10 hover:border-purple-500/50 transition-all hover:scale-105 focus:outline-none focus:ring-2 focus:ring-purple-500"
                                >
                                    <Image
                                        src={example.url}
                                        alt={example.label}
                                        fill
                                        sizes="(max-width: 768px) 100vw, 33vw"
                                        priority={idx === 0}
                                        className="object-cover transition-transform group-hover:scale-110"
                                    />
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent flex items-end p-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                                        <span className="text-white text-xs font-medium truncate w-full text-center">
                                            {example.label}
                                        </span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Loading State */}
                {isDetecting && (
                    <div className="flex flex-col items-center justify-center py-12">
                        <Loader2 className="w-12 h-12 text-purple-400 animate-spin mb-4" />
                        <p className="text-gray-300">Analyzing image with Owlv2...</p>
                    </div>
                )}

                {/* Error State */}
                {error && (
                    <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-xl mb-8">
                        <p className="text-red-400 text-center">{error}</p>
                    </div>
                )}

                {/* Results */}
                {results.length > 0 && (
                    <div className="space-y-8 mb-12">
                        {/* Bounding Box Visualization */}
                        <div>
                            <h2 className="text-2xl font-bold text-white mb-4">
                                Visual Detection
                            </h2>
                            <BoundingBoxCanvas
                                imageUrl={imagePreview!}
                                detections={results}
                                className="mb-6"
                            />
                        </div>

                        {/* Detection Results List */}
                        <div>
                            <h2 className="text-2xl font-bold text-white mb-4">
                                Detected Items ({results.length})
                            </h2>

                            <div className="grid md:grid-cols-2 gap-4">
                                {results.map((result, index) => (
                                    <div
                                        key={index}
                                        className="p-6 bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl hover:border-purple-500/50 transition-colors"
                                    >
                                        <div className="flex justify-between items-start mb-3">
                                            <h3 className="text-lg font-semibold text-white capitalize">
                                                {result.label}
                                            </h3>
                                            <span className="px-3 py-1 bg-purple-500/20 text-purple-300 rounded-full text-sm font-medium">
                                                {(result.score * 100).toFixed(1)}%
                                            </span>
                                        </div>

                                        <div className="text-sm text-gray-400 space-y-1 mb-4">
                                            <p>Position: ({result.box.xmin.toFixed(2)}, {result.box.ymin.toFixed(2)})</p>
                                            <p>
                                                Size: {(result.box.xmax - result.box.xmin).toFixed(2)} × {' '}
                                                {(result.box.ymax - result.box.ymin).toFixed(2)}
                                            </p>
                                        </div>

                                        <button
                                            onClick={() => handleSearchSimilar(result)}
                                            disabled={isSearching}
                                            className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 text-white rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
                                        >
                                            <Search className="w-4 h-4" />
                                            Search Similar Products
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* Search Results */}
                {searchResults.length > 0 && (
                    <div className="mb-12">
                        <SearchResults results={searchResults} isLoading={isSearching} />
                    </div>
                )}

                {/* Searching State */}
                {isSearching && (
                    <div className="flex flex-col items-center justify-center py-12">
                        <Loader2 className="w-12 h-12 text-purple-400 animate-spin mb-4" />
                        <p className="text-gray-300">Searching for similar products...</p>
                    </div>
                )}
            </main>

            {/* Footer */}
            <footer className="border-t border-white/10 mt-auto">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <p className="text-center text-gray-400">
                        Built by {' '}
                        <a
                            href="https://github.com/Abhics8"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-purple-400 hover:text-purple-300 transition-colors"
                        >
                            Abhi Bhardwaj
                        </a>
                        {' • '} Open Source
                    </p>
                </div>
            </footer>
        </div>
    );
}
